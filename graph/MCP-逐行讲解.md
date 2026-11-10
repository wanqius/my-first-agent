# MCP 三个文件 · 逐行讲解

> 对象：`mcp_server.py`（32 行）、`mcp_client_demo.py`（40 行）、`04_agent_mcp.py`（150 行）
> 环境：Python 3.12 + `mcp 2.3.0` + `langgraph 1.x`
> 读法：先看第零节（语法补丁），再按文件顺序读。行号与磁盘上的文件一一对应。

---

# 零、先补 6 个 Python 语法

这三个文件用到的「不属于基础语法」的东西，只有下面 6 个。

## ① 装饰器 `@server.tool()`

```python
@server.tool()
def get_today() -> str:
    ...
```

**一句话**：`@` 这一行，等于**把下面这个函数交给 `server` 登记**。

**等价于（不用装饰器的写法）**：

```python
def get_today() -> str:
    ...

server.tool()(get_today)     # 手工登记
```

**装饰器干了三件事**（这也是为什么你一行工具清单都没写）：

1. 把函数**存进** server 的工具表
2. 读函数的**名字** → 工具名 `get_today`
3. 读函数的**类型标注和 docstring** → 生成参数 schema 和描述

> 所以：**函数名 = 工具名，docstring = 工具描述，类型标注 = 参数类型。** 一个都不能马虎。

---

## ② `async def` 与 `await`

```python
async def main():
    result = await session.call_tool("get_today", {})
```

| 词 | 含义 |
|---|---|
| `async def` | 这是一个**异步函数**，调用它不会立刻执行完，而是返回一个"待完成"的对象 |
| `await` | **在这里等**，等的时候把 CPU 让给别人 |

**为什么需要**：你要等**另一个进程**回话。等待期间程序不能干等着，得让出去。

**规则**：`await` 只能写在 `async def` 里面；`async def` 的函数要用 `await` 或 `asyncio.run()` 来启动。

---

## ③ `async with`

```python
async with stdio_client(params) as (read, write):
    ...
```

普通 `with` 是"打开 → 用完自动关"。`async with` 是它的异步版本：**关闭动作本身也要等待**（要通知对面的进程退出）。

**关键**：`async with` 结束 = **会话关了**。所以所有用到 `session` 的代码，都必须写在它的缩进里。

---

## ④ `with ... as f`

```python
with open("run.log", "a", encoding="utf-8") as f:
    f.write(line + "\n")
```

**一句话**：打开文件，**离开这段缩进就自动关闭**。不用手写 `f.close()`，也不会因为异常忘了关。

---

## ⑤ 类型标注 `text: str`

```python
def count_words(text: str) -> int:
```

- `text: str` = 参数名叫 `text`，**应该是**字符串
- `-> int` = **返回值是**整数

**Python 不会强制检查**——你传个数字进去照样能跑。**但 MCP 会读它**，用来生成参数 schema：

```json
{"properties": {"text": {"type": "string"}}, "required": ["text"]}
```

> **这就是"工具描述自动生成"的全部来源。** 不是魔法，就是读了你的标注。

---

## ⑥ `*parts`、`f""`、`%`

```python
def log(*parts):                     # 任意个参数 → 打包成元组
    print(" ".join(str(p) for p in parts))

f"- {t.name}: {t.description}"       # f-string：{} 里放变量
"  [%d 条] %s" % (n, text)           # 老式格式化：%d 整数、%s 字符串
```

**三种写法干同一件事：把变量塞进字符串。** 见到不用慌。

---

# 一、`mcp_server.py` 逐行（32 行）

## 第 1~5 行

```python
"""最小的 MCP Server：通过标准协议对外暴露工具。

启动方式（默认 stdio，由客户端拉起）：
    .venv\\Scripts\\python.exe graph\\mcp_server.py
"""
```

**在干什么**：文件说明（三引号字符串）。

**注意**：这不是普通注释，是 **docstring**——模块级说明。工具函数的 docstring 会被 MCP 读去当描述，模块级的只是给人看。

---

## 第 7 行

```python
import datetime
```

**在干什么**：借日期工具箱，第 17 行用 `datetime.date.today()`。

---

## 第 9 行

```python
from mcp.server.mcpserver import MCPServer
```

**在干什么**：从 MCP SDK 里取 `MCPServer` 这个类。

**版本坑**：1.x 叫 `FastMCP`（`from mcp.server.fastmcp import FastMCP`）。**2.x 改名了**，照抄老教程会 `ModuleNotFoundError`。

---

## 第 11 行

```python
server = MCPServer("my-tools")
```

**在干什么**：创建一个 server 实例，名字叫 `my-tools`。

**这个名字是给客户端看的**，出现在握手阶段。**它不参与工具调用**，改它不影响功能。

---

## 第 14 行

```python
@server.tool()
```

**在干什么**：把下面这个函数**登记成工具**。

**括号不能省**：`@server.tool` （不带括号）是另一种用法，会传错东西。**记住带括号。**

---

## 第 15 行

```python
def get_today() -> str:
```

**在干什么**：定义一个普通函数，返回字符串。

**MCP 从这一行读到两件事**：工具名 = `get_today`；**没有参数**（括号是空的）。

---

## 第 16 行

```python
    """查询今天的日期，格式 YYYY-MM-DD。不需要参数。"""
```

**在干什么**：函数说明。

**这一行就是客户端打印出来的"工具描述"**，也是模型判断"该不该用这个工具"的依据。

> **写得含糊，模型就会选错。** 第 28 行那个 `count_chars` 之所以能被正确选中，全靠这里写了"不含空格"。

---

## 第 17 行

```python
    return datetime.date.today().isoformat()
```

**在干什么**：取今天，转成 `2026-11-10` 这种字符串。

`.isoformat()` 把日期对象变成标准格式字符串——**模型读得懂，也方便拼进回答**。

---

## 第 20~23 行

```python
@server.tool()
def count_words(text: str) -> int:
    """统计一段文字有多少个字符（含空格）。需要参数 text。"""
    return len(text)
```

**在干什么**：第二个工具，**需要参数**。

**和 `get_today` 的唯一区别**：括号里有 `text: str`。MCP 据此生成：

```json
{"properties": {"text": {"type": "string"}}, "required": ["text"]}
```

**`required` 就是这么来的**——有类型标注、没默认值 → 必填。

---

## 第 25~28 行

```python
@server.tool()
def count_chars(text: str) -> int:
    """统计一段文字的字符数（不含空格）。需要参数 text。"""
    return len(text.replace(" ", ""))
```

**在干什么**：第三个工具。

`text.replace(" ", "")` = 把**所有空格换成空串**（等于删掉空格），再数长度。

**为什么加它**：为了验证"加工具不用改客户端"，以及**考察模型能不能分清两个相似工具**。

---

## 第 31~32 行

```python
if __name__ == "__main__":
    server.run()  # 默认 stdio
```

**第 31 行在干什么**：只有**直接运行这个文件**时才执行；被 import 时不执行。

**为什么需要**：客户端是通过"启动这个文件"来用它的，不需要 import。

**第 32 行在干什么**：启动服务，**默认用 stdio**（标准输入输出）。

**stdio 的含义**：不监听端口、不走网络。**客户端把消息写进这个进程的 stdin，这个进程把回答写进 stdout。**

> ⚠️ **绝对不要在 server 里 `print()`**。stdout 是协议通道，你打一行字，协议就被污染，客户端会报解析错误。要打日志请写 `file=sys.stderr`。

---

# 二、`mcp_client_demo.py` 逐行（40 行）

## 第 7~8 行

```python
import asyncio
import sys
```

**在干什么**：

| 模块 | 用来干什么 |
|---|---|
| `asyncio` | 第 40 行 `asyncio.run(main())`，启动异步程序 |
| `sys` | 第 14 行 `sys.executable`，拿到**当前 python 的完整路径** |

---

## 第 10~11 行

```python
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
```

| 名字 | 是什么 |
|---|---|
| `ClientSession` | 会话对象：`list_tools` / `call_tool` 都在它身上 |
| `StdioServerParameters` | "怎么启动对面那个进程"的配置 |
| `stdio_client` | 真正去启动进程、建管道 |

---

## 第 13~16 行

```python
SERVER = StdioServerParameters(
    command=sys.executable,
    args=["graph/mcp_server.py"],
)
```

**在干什么**：写好"启动命令"。

**翻译成人话**：**用当前这个 python，去跑 `graph/mcp_server.py`。**

**为什么用 `sys.executable` 而不是 `"python"`**：

| 写法 | 风险 |
|---|---|
| `"python"` | 可能指向系统里另一个 python（没装 mcp）→ 对面启动即崩 |
| **`sys.executable`** | **一定是当前这个 venv 的 python**，包齐全 |

> 这是 MCP 最常见的一类故障：**对面进程启动了，但用的是错的解释器**。

**`args` 里是相对路径**：所以**必须在仓库根目录运行**，否则找不到文件。

---

## 第 19 行

```python
async def main():
```

**在干什么**：定义一个异步函数，所有逻辑放里面。

---

## 第 20 行

```python
    async with stdio_client(SERVER) as (read, write):
```

**在干什么**：**启动对面进程，建两根管子**。

| 变量 | 是什么 |
|---|---|
| `read` | 从对面**读**消息的流 |
| `write` | 往对面**写**消息的流 |

**退出这个 `async with` = 进程被关掉。** 所以第 21 行开始的所有代码都在它里面。

---

## 第 21 行

```python
        async with ClientSession(read, write) as session:
```

**在干什么**：把两根管子包成一个**会话**，之后所有请求都用 `session` 发。

**为什么要包一层**：`ClientSession` 负责协议的细节——给消息编号、等对应的回复、处理错误。**你不用手写 JSON-RPC。**

---

## 第 22 行

```python
            await session.initialize()
```

**在干什么**：握手。

**报什么**：客户端说自己支持的协议版本、自己是谁；服务端回它支持的版本、它的名字（`my-tools`）。

**不做会怎样**：后面的请求会被拒。

---

## 第 25 行

```python
            tools = await session.list_tools()
```

**在干什么**：问对面：**你有哪些工具？**

**返回什么**：一个对象，`.tools` 是列表，每个元素有 `name` / `description` / `input_schema`。

---

## 第 27~29 行

```python
            for t in tools.tools:
                print(f"  - {t.name}: {t.description}")
                print(f"    参数 schema: {t.input_schema}")
```

**在干什么**：逐个打印。

**`t.input_schema`** 就是第 21 行那个函数标注生成的 JSON：

```json
{"properties": {"text": {"type": "string"}}, "required": ["text"], "type": "object"}
```

> **版本坑**：1.x 里这个字段叫 `inputSchema`（驼峰）。2.x 改成 `input_schema`（下划线）。写错会抛 `ExceptionGroup`，报错信息里根本看不出是这个原因。

---

## 第 32 行

```python
            result = await session.call_tool("get_today", {})
```

**在干什么**：调用工具。

| 参数 | 含义 |
|---|---|
| `"get_today"` | 工具名（**字符串**，不是函数） |
| `{}` | 参数字典（这个工具不要参数，所以空） |

**注意**：传的是**名字**。你手里**没有** `get_today` 这个函数——它在对面进程里。

---

## 第 33 行

```python
            print("\n调用 get_today →", result.content)
```

**在干什么**：打印结果。

`result.content` 是个**列表**，每项是一个内容块，典型长这样：

```
[TextContent(type='text', text='2026-11-10', annotations=None, meta=None)]
```

**为什么是列表**：协议允许一次返回多块内容（文字、图片、文件）。**要取文字，得从每块里拿 `.text`**——`04_agent_mcp.py` 第 115 行就是这么干的。

---

## 第 35~36 行

```python
            result2 = await session.call_tool("count_words", {"text": "今天 心情 很好"})
            print("调用 count_words →", result2.content)
```

**在干什么**：带参数调第二个工具。

**参数是普通字典**：键名必须和 schema 里的 `properties` 一致（这里是 `text`）。**写错键名，服务端会报参数校验失败。**

---

## 第 40 行

```python
    asyncio.run(main())
```

**在干什么**：启动事件循环，跑 `main()` 到结束。

**`async def` 不能直接调用**——`main()` 只会返回一个"待完成对象"，必须交给 `asyncio.run` 才会真正执行。

---

# 三、`04_agent_mcp.py` 逐行（150 行）

## 第 1~8 行：文件说明

```python
"""通过 MCP 使用工具的 Agent —— 与 03_agent_graph.py 对照版。
...
"""
```

**在干什么**：告诉读的人"这版和 03 差在哪"。**两处**：工具清单来源、分发方式。

---

## 第 10~21 行：import

```python
import asyncio          # 第 10 行：新增，第 152 行 asyncio.run
import datetime         # 日志时间戳
import json             # 解析模型输出的 JSON
import operator         # State 的合并规则
import os               # 读环境变量里的 Key
import sys              # 拿当前 python 路径，去启动 server
from typing import Annotated, TypedDict
import requests                             # 调 DeepSeek
from langgraph.graph import END, START, StateGraph
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
```

**和 `03_agent_graph.py` 比，多了 3 个**：`asyncio`、`sys`、两个 `mcp` 的导入。

---

## 第 24~25 行：State（与 03 完全相同）

```python
class State(TypedDict):
    messages: Annotated[list, operator.add]
```

**在干什么**：记录本规格 + 自动续页。**没有任何改动。**

---

## 第 28~32 行：`log()`（与 03 相同）

```python
def log(*parts):
    line = datetime.datetime.now().strftime("%H:%M:%S") + "  " + " ".join(str(p) for p in parts)
    print(line)
    with open("run.log", "a", encoding="utf-8") as f:
        f.write(line + "\n")
```

**在干什么**：时间戳 + 屏幕 + 落盘。**原样搬来。**

---

## 第 35~56 行：`ask()`（与 03 相同）

```python
def ask(msgs):
    r = None
    try:
        r = requests.post(...)
        data = r.json()
    except Exception as e:
        log("[网络]", ...)
        if r is not None:
            log("[诊断]", ...)
        return None
    if "error" in data:
        ...
        return None
    return data["choices"][0]["message"]["content"]
```

**在干什么**：调 DeepSeek，失败返回 `None`。**原样搬来，一个字没改。**

---

## 第 59~65 行：`call_model`（与 03 相同）

```python
def call_model(state):
    reply = ask(state["messages"])
    if reply is None:
        ...
    log("[模型]", reply[:80])
    return {"messages": [{"role": "assistant", "content": reply}]}
```

**在干什么**：节点①。**注意它是普通 `def`，不是 `async def`**——因为调 DeepSeek 用的是同步的 `requests`。

> LangGraph **允许同步节点和异步节点混用**：`astream` 跑的时候，同步节点会被丢到线程池里执行。

---

## 第 68~79 行：`route`（与 03 相同）

```python
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
```

**在干什么**：三个出口——结束 / 拦截重复 / 去调工具。**原样搬来。**

**为什么它必须留着**：Server 只管"执行一次"，**不管你有没有原地打转**。打转是流程问题，归 Host。

---

## 第 82 行

```python
async def main():
```

**在干什么**：从这里开始全部改成异步——因为要跟另一个进程说话。

---

## 第 83 行

```python
    params = StdioServerParameters(command=sys.executable, args=["graph/mcp_server.py"])
```

**在干什么**：写"启动命令"。

**这一行就是"MCP 有两个进程"的物证。** `command` 是要跑的解释器，`args` 是要跑的文件。

---

## 第 85 行

```python
    async with stdio_client(params) as (read, write):
```

**在干什么**：**启动对面进程**，拿到读/写两根管子。

**从这里开始，缩进内的代码全部依赖这个进程活着。** 一旦退出缩进，进程被杀。

---

## 第 86~87 行

```python
        async with ClientSession(read, write) as session:
            await session.initialize()
```

**在干什么**：包成会话 + 握手。**之后所有 `session.xxx` 都基于这条已建立的连接。**

---

## 第 90~92 行

```python
            tools = await session.list_tools()
            tools_text = "\n".join(f"- {t.name}: {t.description}" for t in tools.tools)
            log("[MCP]", "发现工具", len(tools.tools), "个")
```

**在干什么**：**把工具清单问出来，拼成提示词里的几行字。**

| 行 | 作用 |
|---|---|
| 90 | 问 Server 要清单 |
| 91 | 每个工具拼成 `- 名字: 描述`，换行连接 |
| 92 | 记一笔"发现 3 个" |

**`"\n".join(...)`**：把一个列表用换行拼成一个字符串。

**这一行就是"工具清单不用手写"的全部实现。** 对比 03 里那段写死的 6 行——现在由 Server 提供，加工具自动出现。

---

## 第 95 行

```python
            async def run_tool(state):
```

**在干什么**：定义节点②，**注意是 `async def`**。

**为什么定义在 `main()` 里面**：因为它要用外面的 `session`。**写在外面就访问不到 `session` 了**（作用域）。

> 这是本次改造在结构上最"别扭"的一点：**节点依赖会话，会话是运行时才有的**，所以节点只能在里面定义。

---

## 第 96~104 行：解析（与 03 相同）

```python
                text = state["messages"][-1]["content"]
                s, e = text.find("{"), text.rfind("}")
                call = None
                if s != -1 and e != -1:
                    try:
                        call = json.loads(text[s:e + 1])
                    except Exception as ex:
                        log("[兜底]", "JSON 解析失败：", type(ex).__name__)
```

**在干什么**：取出最后一条消息，把里面的 JSON 抠出来。

**和 03 完全一样**——这部分跟 MCP 无关，**模型输出格式不变**。

---

## 第 106~108 行

```python
                if call is None:
                    log("[兜底]", "没有可用的 JSON，已把错误喂回模型")
                    return {"messages": [{"role": "user", "content": "工具调用格式不合法。请只输出一行合法 JSON，不要加任何解释。"}]}
```

**在干什么**：解析失败就**把错误喂回模型**，给它改正机会。

---

## 第 110~111 行

```python
                name = call.get("tool")
                args = call.get("args") or {}
```

**在干什么**：取出工具名和参数。

**`or {}` 的作用**：如果 `args` 是 `None`（模型写了 `"args": null`）或空字典，统一成 `{}`。**不写这句，`None` 传给 `call_tool` 可能出错。**

---

## 第 113~118 行：**核心改动**

```python
                try:
                    res = await session.call_tool(name, args)
                    out = "".join(getattr(c, "text", "") for c in res.content)
                except Exception as ex:
                    out = "工具调用失败：" + type(ex).__name__
                    log("[工具错误]", out)
```

**在干什么**：**把名字和参数原样转给 Server，等它执行完，把结果拼成一段文字。**

### 逐句

| 行 | 在干什么 |
|---|---|
| 113 | 开始兜底（工具名不存在、参数不对、对面崩了，都在这接住） |
| **114** | **一行替代了 03 里的整个 `if/elif` 分发** |
| 115 | 把返回的多个内容块里的 `.text` 拼成一个字符串 |
| 116~118 | 出错就变成一句"工具调用失败：XXX"，**不崩** |

### 为什么 `if/elif` 没了

| | `03_agent_graph.py` | 这里 |
|---|---|---|
| 谁决定 name 对应哪个函数 | **你**（手写分支） | **Server** |
| 加一个工具要改哪 | 提示词 + 分支 + 工具函数 | **只改 server** |

**`call_tool` 内部就是 `if name == ...` 的分发——只不过在对面进程里，你写一次就够了。**

### `getattr(c, "text", "")` 为什么这么写

`res.content` 是列表，里面可能是文字块、图片块……**只有文字块有 `.text`**。

`getattr(对象, 属性名, 默认值)` = **有就取，没有就给空串**，不会因为缺属性崩。

---

## 第 120~121 行

```python
                log("[工具]", name, "→", out[:60])
                return {"messages": [{"role": "user", "content": "工具返回：" + out + "，请继续完成任务；如果已经完成，就直接回答。"}]}
```

**在干什么**：记日志 + 把结果写回记录本。

**和 03 唯一的差别**：`result` 变成了 `out`（一段文字）。**格式、提示语、role 全部不变。**

---

## 第 123~129 行：拼图（与 03 相同）

```python
            builder = StateGraph(State)
            builder.add_node("call_model", call_model)
            builder.add_node("run_tool", run_tool)
            builder.add_edge(START, "call_model")
            builder.add_conditional_edges("call_model", route, {"tool": "run_tool", "end": END})
            builder.add_edge("run_tool", "call_model")
            graph = builder.compile()
```

**在干什么**：两个节点、入口、条件边、回环。**一行没改。**

> 注意 125 行：`run_tool` 是个 `async def`，但注册方式完全一样。**LangGraph 不看你是不是异步，只看能不能调。**

---

## 第 131~138 行：system 提示词

```python
            system = f"""你可以使用以下工具（由 MCP Server 提供）：

{tools_text}

需要用工具时，你的整条回复只能是一行 JSON，前后不要有任何文字：
{{"tool": "工具名", "args": {{"参数名": 值}}}}

不需要工具时，直接回答。"""
```

**在干什么**：拼提示词。**工具清单那一段是变量 `{tools_text}` 插进来的。**

### 为什么 JSON 示例里的花括号是双的

`f"""..."""` 里，**`{}` 是"插变量"的语法**。要输出一个**真正的花括号**，必须写两次：`{{` → `{`。

所以：

| 你写的 | 输出的 |
|---|---|
| `{tools_text}` | 变量内容 |
| `{{"tool": ...}}` | 字面的 `{"tool": ...}` |

**漏写一个花括号，程序会报 `SyntaxError` 或插错值。**

---

## 第 140 行以后：`init` 与 `astream`

```python
            init = {"messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": "昨天是几号？……"},
            ]}

            async for chunk in graph.astream(init, {"recursion_limit": 10}, stream_mode="values"):
                last = chunk["messages"][-1]
                print("  [%d 条] %s" % (len(chunk["messages"]), last["content"][:40].replace("\n", " ")))
```

**在干什么**：准备初始记录本，然后逐步跑图。

**`stream` → `astream`**：因为图里有一个异步节点，**必须用异步版跑**。

**`async for`**：一步一步拿结果，每步拿一次。

---

## 第 152 行

```python
    asyncio.run(main())
```

**在干什么**：启动整个异步程序。

**位置很关键**：它在 `if __name__ == "__main__":` 里面（第 151 行），**不在 `main()` 内部**——因为 `asyncio.run` 是"启动器"，不能自己启动自己。

---

# 四、一次运行，数据到底长什么样

以「昨天是几号？另外'今天 心情 很好'有多少个字符（不含空格）」为例。

| 步 | 谁做的 | 发出/收到什么 |
|---|---|---|
| 0 | 客户端 | 启动 `mcp_server.py`（第二个进程） |
| 1 | 客户端 | `initialize` → Server 回：版本 + `my-tools` |
| 2 | 客户端 | `tools/list` → 回 3 个工具的名字、描述、schema |
| 3 | 客户端 | 把 3 行工具清单拼进 system，**整本记录本发给 DeepSeek** |
| 4 | 模型 | 回 `{"tool": "get_today", "args": {}}` |
| 5 | 客户端 | `tools/call` `get_today` → Server 执行 → 回 `2026-11-10` |
| 6 | 客户端 | 把 `工具返回：2026-11-10…` 写进记录本，**再发一次** |
| 7 | 模型 | 回 `{"tool": "count_chars", "args": {"text": "今天 心情 很好"}}` |
| 8 | 客户端 | `tools/call` `count_chars` → 回 `6` |
| 9 | 客户端 | 写进记录本，再发一次 |
| 10 | 模型 | 回「昨天是 2026-11-09；……共 6 个字符。」 |
| 11 | `route` | 没有 `{` → `end`，图结束 |

**记录本条数**：`2 → 3 → 4 → 5 → 6 → 7`。

**MCP 只参与了第 2、5、8 步**——其余全是你原来那套。

---

# 五、四个高频错误

| 现象 | 根因 | 修法 |
|---|---|---|
| `ModuleNotFoundError: mcp.server.fastmcp` | 用了 1.x 的导入 | 2.x 是 `from mcp.server.mcpserver import MCPServer` |
| `ExceptionGroup` 且看不出原因 | 多半是 `t.inputSchema`（1.x 字段名） | 2.x 用 `t.input_schema` |
| 对面进程一启动就退出 | `command` 用的不是装过 mcp 的 python | 用 `sys.executable` |
| 客户端解析错误、连不上 | server 里 `print()` 污染了 stdout | 日志写 `file=sys.stderr` |

---

# 六、和 `03_agent_graph.py` 的对照

| 位置 | 03（工具写死） | 04（MCP） |
|---|---|---|
| 工具定义 | 本文件里三个函数 | **`mcp_server.py`（另一个进程）** |
| 工具清单 | 手写 6 行提示词 | `list_tools()` 自动生成 |
| 分发 | `if/elif` 三支 | `await session.call_tool(name, args)` |
| 工具节点 | `def` | `async def` |
| 运行 | `graph.stream(...)` | `graph.astream(...)` |
| 加工具要改 | 提示词 + 分支 + 函数（3 处） | **只改 server（1 处）** |
| 循环/判断/日志/兜底 | 本文件 | **仍在本文件（MCP 不管这些）** |

**一句话**：**MCP 换掉的是"能力从哪来"，没换"流程怎么走"。**
