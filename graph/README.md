# LangGraph + MCP 智能体

> 一个能用自然语言调工具的智能体：**LangGraph 负责流程编排，MCP 负责工具供给，FastAPI 负责对外服务**。
> 24 条评测用例全部通过；工具由独立进程提供，Agent 不写死任何工具。

---

## 一、它长什么样

```
浏览器  http://127.0.0.1:8000/
   │  POST /chat  {"question": "今天几号？"}
   ▼
FastAPI（api_server.py）
   │  lifespan 里建一条 MCP 连接，所有请求共用
   ▼
LangGraph 图（agent_core.py）
   │  call_model ──条件边──→ run_tool ──回环──→ call_model
   │      │                      │
   │      ▼                      ▼
   │   DeepSeek                MCP Client
   │                          │
   │                  stdio 管道（JSON）
   │                          ▼
   │                 mcp_server.py（独立进程）
   │                   get_today / count_words / count_chars
   ▼
{"answer": "...", "calls": ["get_today"], "elapsed_ms": 2407}
```

**一句话**：左边是"会思考的"，右边是"会干活的"，中间用标准协议连起来。

---

## 二、四个能力

| 能力 | 实现 |
|---|---|
| **自己判断要不要用工具** | 图里的条件边 `route`：模型这一轮说话里带 JSON，就去跑工具 |
| **多步执行** | `run_tool → call_model` 回环；一个问题需要两次工具就转两圈 |
| **工具与 Agent 解耦** | 工具在独立进程（MCP Server），加工具**只改 server**，Agent 零改动 |
| **对外提供接口** | FastAPI：`/chat` 问答、`/health` 健康检查、`/` 网页界面、`/docs` 接口文档 |

---

## 三、怎么跑

```powershell
# 1. 建环境（Python ≥ 3.10，本项目用 3.12）
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

# 2. 配置 Key（不要写进代码）
setx DEEPSEEK_API_KEY "sk-你的key"
# 设完要重开终端

# 3. 启动服务
.\.venv\Scripts\python.exe graph\api_server.py
```

然后打开 **http://127.0.0.1:8000/** —— 输入框 + 示例按钮。
接口文档在 **/docs**（可以点着调）。

### 只想跑命令行版

```powershell
.\.venv\Scripts\python.exe graph\04_agent_mcp.py
```

### 想跑评测

```powershell
.\.venv\Scripts\python.exe graph\eval_run.py
```

---

## 四、评测结果

24 条用例，6 类场景，**当前 24/24 = 100%**。

| 类型 | 条数 | 考察什么 | 通过 |
|---|---|---|---|
| 单工具 | 4 | 会不会调无参工具 | 4/4 |
| 带参数 | 4 | 参数抽取准不准 | 4/4 |
| 多步 | 4 | 两个工具的先后顺序 | 4/4 |
| 不用工具 | 4 | 闲聊时会不会瞎调 | 4/4 |
| 该失败 | 4 | 没这个能力时会不会编 | 4/4 |
| 对抗 | 4 | 指令冲突 / 长句 / 链式依赖 / 缺参数 | 4/4 |

**判分规则**：`calls`（工具调用序列）与期望完全一致 **且** 回答含关键信息，两条都过才算通过。

### 这个 100% 是怎么来的

| 轮 | 分数 | 发现的问题 |
|---|---|---|
| v1 | 16/20 | 2 条**评测器 bug**（「11 月 16 日」vs「11月16日」，比对没去空格）+ 2 条**用例歧义**（无空格时两个工具同结果） |
| v2 | 20/20 | 题太简单，测不出差距 |
| v3 | 23/24 | 又一条用例没区分力 |
| 最终 | **24/24** | —— |

**敏感性验证**：把 MCP Server 换成只剩 `get_today` 的残缺版，8 条相关用例从 **8/8 掉到 2/8** —— 证明这套题真的能测出问题。

> 有意思的发现：残缺版里模型**没有工具也把字数算对了**（答案对、过程错）。所以判分必须同时看"用了该用的工具"和"答案对不对"。

---

## 五、四个设计决策

### ① State 用 `Annotated[list, operator.add]`

节点只需返回 `{"messages": [新消息]}`，框架自动接在末尾。

去掉 `Annotated` 不会报错，但**每轮都会覆盖前文** —— Agent 当场失忆。这是最隐蔽的一个坑。

### ② 回环用固定边，停止用条件边

```python
builder.add_conditional_edges("call_model", route, {"tool": "run_tool", "end": END})
builder.add_edge("run_tool", "call_model")
```

- **出去**：谁去谁留，由 `route` 判断
- **回来**：工具跑完无条件回模型（模型必须看到结果才能继续想）

### ③ 工具放在独立进程（MCP）

`StdioServerParameters(command=sys.executable, args=["mcp_server.py"])` —— **启动第二个 python 进程**，用 stdio 管道以 JSON 一问一答。

加工具只改 `mcp_server.py`，`agent_core.py` **一行不动**。工具清单通过 `list_tools()` 自动读出，拼进提示词。

### ④ 服务化：连接复用 + 串行化

- `lifespan` 里连一次 MCP，全服务共用（否则每个请求拉起一个进程）
- `asyncio.Lock` 排队（一条 MCP 连接不能并发，否则请求/响应会串）

---

## 六、踩过的坑（都真踩过）

| 现象 | 根因 | 修法 |
|---|---|---|
| 记录本越用越短，模型"失忆" | State 字段少了 `operator.add`，每轮覆盖 | 加合并规则 |
| 任务做一半就结束 | 用 `startswith("{")` 判断，模型把 JSON 放在人话后面 | 改成 `"{" in ...` + `find/rfind` 抠出来 |
| 模型答"我没有访问系统时间的能力" | 提示词里写了占位符 `……原样不动……` | 提示词写错不报错，只让模型变笨 |
| `JSONDecodeError: char 0` 看起来像断网 | 接口地址少了个 `s`（`completion` vs `completions`），404 页面不是 JSON | 异常类型 ≠ 根因 |
| `Run.log` 打开全是乱码 | 文件是 UTF-8，PowerShell 5.1 按 GBK 读 | `Get-Content -Encoding UTF8` |
| `ModuleNotFoundError: mcp.server.fastmcp` | 网上教程是 mcp 1.x | 2.x 用 `mcp.server.mcpserver.MCPServer` |
| curl 调接口返回 422 | PowerShell 吃掉 `\"` 转义 | 用 `/docs` 页面，或 `--data-binary @file.json` |

---

## 七、目录

| 文件 | 说明 |
|---|---|
| `api_server.py` | FastAPI 服务：`/`、`/health`、`/chat`、`/docs` |
| `agent_core.py` | Agent 核心：State、节点、路由、`run_agent()` |
| `mcp_server.py` | MCP Server（独立进程），暴露 3 个工具 |
| `mcp_client_demo.py` | 最小 MCP 客户端：握手 → 要清单 → 调工具 |
| `04_agent_mcp.py` | 命令行版 Agent（接 MCP） |
| `03_agent_graph.py` | 命令行版 Agent（工具写死），用于对照 |
| `eval_cases.py` / `eval_run.py` | 24 条评测用例 + 自动判分 |
| `web/index.html` | 网页界面 |
| `逐行讲解.md` | 01/02/03 逐行（五版） |
| `MCP-逐行讲解.md` | MCP 三个文件逐行（含 Python 语法补丁） |

---

## 八、已知限制

1. **无鉴权** —— 只适合本机跑，对外暴露前必须加
2. **并发 = 1** —— 一条 MCP 连接串行处理，第二个请求要排队
3. **无流式输出** —— 要等完整回答，不能逐字显示
4. **单轮问答** —— 没有多轮对话状态，每次请求独立
5. **24 条用例是小样本** —— 覆盖不到长文本、并发、多轮
6. **未容器化** —— 换机器要重建环境
