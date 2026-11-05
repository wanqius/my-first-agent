import os                                    # 新增
import json                                  # 新增
import datetime                              # 新增
import operator
import requests                              # 新增
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, START, END


class State(TypedDict):
    messages: Annotated[list, operator.add]

def log(*parts):
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
    if reply is None:                                        # 新增
        log("[中止]", "本轮调用失败，任务停止")                # 新增
        return {"messages": [{"role": "assistant", "content": "（模型调用失败，任务中止）"}]}   # 新增
    log("[模型]", reply[:80])
    return {"messages": [{"role": "assistant", "content": reply}]}

def get_today():
    return datetime.date.today().isoformat()


def count_words(text):
    return len(text)


def run_tool(state):
    text = state["messages"][-1]["content"]
    s, e = text.find("{"), text.rfind("}")

    call = None
    if s != -1 and e != -1:
        try:
            call = json.loads(text[s:e + 1])
        except Exception as ex:
            log("[兜底]", "JSON 解析失败：", type(ex).__name__, str(ex)[:60])

    if call is None:
        log("[兜底]", "没有可用的 JSON，已把错误喂回模型")      # 新增
        return {"messages": [{"role": "user", "content": "工具调用格式不合法。请只输出一行合法 JSON，不要加任何解释。"}]}

    name = call.get("tool")
    args = call.get("args", {})

    if name == "get_today":
        result = get_today()
    elif name == "count_words" and "text" in args:
        result = count_words(args["text"])
    else:
        result = "没有这个工具或缺少参数：" + str(name)

    log("[工具]", name, "→", result)
    return {"messages": [{"role": "user", "content": "工具返回：" + str(result) + "，请继续完成任务；如果已经完成，就直接回答。"}]}

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


builder = StateGraph(State)
builder.add_node("call_model", call_model)
builder.add_node("run_tool", run_tool)
builder.add_edge(START, "call_model")
builder.add_conditional_edges("call_model", route, {"tool": "run_tool", "end": END})
builder.add_edge("run_tool", "call_model")

graph = builder.compile()

init = {
    "messages": [
        {"role": "system", "content": """你有两个工具可用：
1. get_today() —— 查询今天的日期，不需要参数
2. count_words(text) —— 统计一段文字有多少个字，需要参数 text

需要用工具时，你的整条回复只能是一行 JSON，前后不要有任何文字：
{"tool": "工具名", "args": {"参数名": 值}}

不需要工具时，直接回答。"""},
        {"role": "user", "content": "昨天是几号"},
    ]
}


for chunk in graph.stream(init, {"recursion_limit": 8}, stream_mode="values"):
    last = chunk["messages"][-1]
    print("  [%d 条] %s" % (len(chunk["messages"]), last["content"][:40].replace("\n", " ")))
print(graph.get_graph().draw_mermaid())



