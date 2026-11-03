from typing import TypedDict
from langgraph.graph import StateGraph, START, END


class State(TypedDict):
    n: int


def add_one(state):
    return {"n": state["n"] + 1}


builder = StateGraph(State)
builder.add_node("add_one", add_one)
builder.add_edge(START, "add_one")
builder.add_edge("add_one", END)

graph = builder.compile()

print(graph.invoke({"n": 0}))
