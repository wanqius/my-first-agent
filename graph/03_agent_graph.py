import os                                    # 新增
import json                                  # 新增
import datetime                              # 新增
import operator
import requests                              # 新增
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, START, END


class State(TypedDict):
    messages: Annotated[list, operator.add]


def ask(msgs):                               # 新增：整段从 agent.py 搬来
    r = requests.post(
        "https://api.deepseek.com/chat/completions",
        headers={"Authorization": "Bearer " + os.environ.get("DEEPSEEK_API_KEY", "")},
        json={"model": "deepseek-chat", "messages": msgs, "temperature": 0},
        proxies={"http": None, "https": None},
        timeout=30,
    )
    return r.json()["choices"][0]["message"]["content"]


def call_model(state):
    reply = ask(state["messages"])
    print("  模型说：", reply)
    return {"messages": [{"role": "assistant", "content": reply}]}

def get_today():
    return datetime.date.today().isoformat()


def count_words(text):
    return len(text)


def run_tool(state):
    text = state["messages"][-1]["content"]
    s, e = text.find("{"), text.rfind("}")
    call = json.loads(text[s:e + 1])
    name = call.get("tool")
    args = call.get("args", {})

    if name == "get_today":
        result = get_today()
    elif name == "count_words" and "text" in args:
        result = count_words(args["text"])
    else:
        result = "没有这个工具或缺少参数：" + str(name)

    print("  [工具]", name, "→", result)
    return {"messages": [{"role": "user", "content": "工具返回：" + str(result) + "，请继续完成任务；如果已经完成，就直接回答。"}]}


def route(state):
    last = state["messages"][-1]
    if last["role"] == "assistant" and "{" in last["content"]:
        return "tool"
    return "end"


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
        {"role": "user", "content": "今天几号？"},
    ]
}


for chunk in graph.stream(init, {"recursion_limit": 8}, stream_mode="values"):
    last = chunk["messages"][-1]
    print("  [%d 条] %s" % (len(chunk["messages"]), last["content"][:40].replace("\n", " ")))
print(graph.get_graph().draw_mermaid())



