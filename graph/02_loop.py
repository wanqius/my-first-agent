from typing import TypedDict
from langgraph.graph import StateGraph, START, END


class State(TypedDict):
    n: int


def add_one(state):
    print("  [节点] n =", state["n"], "→", state["n"] + 1)
    return {"n": state["n"] + 1}


def should_continue(state):
    if state["n"] < 3:
        return "again"
    return "done"


builder = StateGraph(State)
builder.add_node("add_one", add_one)
builder.add_edge(START, "add_one")

builder.add_conditional_edges(
    "add_one",
    should_continue,
    {"again": "add_one", "done": END},
)

graph = builder.compile()

print(graph.invoke({"n": 0}))
