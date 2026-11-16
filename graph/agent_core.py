"""Agent 核心（可被 04_agent_mcp.py 与评测脚本复用）。

对外只暴露一个函数：
    result = await run_agent("今天几号？")
    result["answer"]  # 最终回答
    result["calls"]   # 依次调用过的工具名，如 ["get_today"]
"""

import datetime
import json
import operator
import os
import sys
from typing import Annotated, TypedDict

import requests
from langgraph.graph import END, START, StateGraph
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

VERBOSE = False


class State(TypedDict):
    messages: Annotated[list, operator.add]


def log(*parts):
    if not VERBOSE:
        return
    line = datetime.datetime.now().strftime("%H:%M:%S") + "  " + " ".join(str(p) for p in parts)
    print(line)
    with open("run.log", "a", encoding="utf-8") as f:
        f.write(line + "\n")


def ask(msgs):
    r = None
    try:
        r = requests.post(
            "https://api.deepseek.com/chat/completions",
            headers={"Authorization": "Bearer " + os.environ.get("DEEPSEEK_API_KEY", "")},
            json={"model": "deepseek-chat", "messages": msgs, "temperature": 0},
            proxies={"http": None, "https": None},
            timeout=30,
        )
        data = r.json()
    except Exception as e:
        log("[网络]", type(e).__name__, str(e)[:80])
        if r is not None:
            log("[诊断]", r.status_code, repr(r.text[:120]))
        return None

    if "error" in data:
        log("[接口错误]", data["error"].get("message", data["error"]))
        return None

    return data["choices"][0]["message"]["content"]


def call_model(state):
    reply = ask(state["messages"])
    if reply is None:
        log("[中止]", "本轮调用失败，任务停止")
        return {"messages": [{"role": "assistant", "content": "（模型调用失败，任务中止）"}]}
    log("[模型]", reply[:80])
    return {"messages": [{"role": "assistant", "content": reply}]}


def route(state):
    msgs = state["messages"]
    last = msgs[-1]
    if not (last["role"] == "assistant" and "{" in last["content"]):
        return "end"
    for m in reversed(msgs[:-1]):
        if m["role"] == "assistant":
            if m["content"].strip() == last["content"].strip():
                log("[重复]", "检测到相同调用，强制结束")
                return "end"
            break
    return "tool"


async def run_agent(question, max_steps=10, verbose=False, server_script=None):
    """跑一次完整对话，返回 {"answer": str, "calls": [工具名...], "error": bool}"""
    global VERBOSE
    VERBOSE = verbose

    if server_script is None:
        server_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mcp_server.py")

    calls = []
    failed = {"flag": False}

    params = StdioServerParameters(command=sys.executable, args=[server_script])

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            tools_text = "\n".join(f"- {t.name}: {t.description}" for t in tools.tools)
            log("[MCP]", "发现工具", len(tools.tools), "个")

            async def run_tool(state):
                text = state["messages"][-1]["content"]
                s, e = text.find("{"), text.rfind("}")

                call = None
                if s != -1 and e != -1:
                    try:
                        call = json.loads(text[s:e + 1])
                    except Exception as ex:
                        log("[兜底]", "JSON 解析失败：", type(ex).__name__)

                if call is None:
                    log("[兜底]", "没有可用的 JSON，已把错误喂回模型")
                    return {"messages": [{"role": "user", "content": "工具调用格式不合法。请只输出一行合法 JSON，不要加任何解释。"}]}

                name = call.get("tool")
                args = call.get("args") or {}
                calls.append(name)

                try:
                    res = await session.call_tool(name, args)
                    out = "".join(getattr(c, "text", "") for c in res.content)
                except Exception as ex:
                    out = "工具调用失败：" + type(ex).__name__
                    log("[工具错误]", out)

                log("[工具]", name, "→", out[:60])
                return {"messages": [{"role": "user", "content": "工具返回：" + out + "，请继续完成任务；如果已经完成，就直接回答。"}]}

            builder = StateGraph(State)
            builder.add_node("call_model", call_model)
            builder.add_node("run_tool", run_tool)
            builder.add_edge(START, "call_model")
            builder.add_conditional_edges("call_model", route, {"tool": "run_tool", "end": END})
            builder.add_edge("run_tool", "call_model")
            graph = builder.compile()

            system = f"""你可以使用以下工具（由 MCP Server 提供）：

{tools_text}

需要用工具时，你的整条回复只能是一行 JSON，前后不要有任何文字：
{{"tool": "工具名", "args": {{"参数名": 值}}}}

不需要工具时，直接回答。
没有对应工具、或你确实做不到时，直接说明，不要编造。"""

            init = {"messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": question},
            ]}

            final = None
            async for chunk in graph.astream(init, {"recursion_limit": max_steps}, stream_mode="values"):
                final = chunk

            if final is None:
                return {"answer": "", "calls": calls, "error": True}

            return {"answer": final["messages"][-1]["content"], "calls": calls, "error": False}
