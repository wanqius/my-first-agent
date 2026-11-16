# 我的智能体练习集

> 三个从零做起的智能体项目：**低代码平台 → 手写代码 → 框架与工程化**。
> 每个项目都附「踩过的坑」和「已知限制」——这不是作品展示页，是一份学习记录。

---

## 目录

| 目录 | 项目 | 一句话 |
|---|---|---|
| **`agent/`** | 手写多步 Agent | 不靠框架，自己写循环、工具分发、六道保险与记忆 |
| **`memo/`** | 心情小助手 | 第一个手写程序：输入 → 存文件 → 调模型 → 回应 |
| **`graph/`** | **LangGraph + MCP 智能体** | 图编排 + 工具走 MCP 独立进程 + HTTP 接口 + 24 条评测 |
| `examples/` | 实验代码 | 死循环演示等小实验 |

---

## 从哪看起

| 你想看什么 | 打开 |
|---|---|
| **最完整的那个项目** | [`graph/README.md`](graph/README.md) —— 架构、评测、设计决策、坑 |
| Agent 不靠框架怎么运转 | [`agent/README.md`](agent/README.md) |
| 一行一行读懂手写 Agent | [`agent/逐行讲解.md`](agent/逐行讲解.md)（五版全程） |
| 一行一行读懂 LangGraph 与 MCP | [`graph/逐行讲解.md`](graph/逐行讲解.md)、[`graph/MCP-逐行讲解.md`](graph/MCP-逐行讲解.md) |
| 第一个程序长什么样 | [`memo/说明.md`](memo/说明.md) |

---

## 快速开始

需要 Python ≥ 3.10 和一个 DeepSeek API Key。

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

# 设置密钥（不要写进代码）
setx DEEPSEEK_API_KEY "sk-你的key"     # 设完要重开终端
```

```powershell
# ① LangGraph + MCP 版（推荐）
.\.venv\Scripts\python.exe graph\api_server.py
# 浏览器打开 http://127.0.0.1:8000/

# ② 命令行版
.\.venv\Scripts\python.exe graph\04_agent_mcp.py

# ③ 跑评测
.\.venv\Scripts\python.exe graph\eval_run.py

# ④ 不依赖框架的手写版（Python 3.8 即可）
cd agent; python agent.py
```

---

## 学习路径

```
阶段 1  低代码平台（扣子）做出一个可发布的智能体
         ↓  理解了 人设 / 知识库 / 工具 是什么
阶段 2  手写第一个程序 memo/：输入 → 存文件 → 调模型 → 回应
         ↓  理解了 API、文件读写、异常处理
阶段 3  手写 agent/：循环 + 工具分发 + JSON 协议 + 六道保险 + 记忆
         ↓  理解了 Agent 的骨架
阶段 4  graph/：LangGraph 编排 + MCP 工具协议 + 24 条评测 + FastAPI 服务化
         ↓  理解了 调度 / 能力 / 可度量 / 可交付 是四件不同的事
```

**这条路径的关键不是"学过什么"，而是每个阶段都有能跑、能讲清的产物。**

---

## 各部分的能力对比

| | `memo/` | `agent/` | `graph/` |
|---|---|---|---|
| 模型调用 | ✅ | ✅ | ✅ |
| 工具调用 | ❌ | ✅ 写死在代码里 | ✅ **独立进程，MCP 协议** |
| 循环 / 多步 | ❌ | ✅ 手写 `for` | ✅ 图的条件边 + 回环 |
| 故障兜底 | 基础 | ✅ 六道保险 | ✅ 六道保险 + JSON 兜底 |
| 记忆 | ✅ 文件读写 | ✅ 短期 + 长期 | ⬜ 未做 |
| 评测 | ❌ | ❌ | ✅ **24 条用例 + 自动判分** |
| 对外服务 | ❌ | ❌ | ✅ **HTTP 接口 + 网页** |

---

## 这个仓库的原则

1. **不藏坑** —— 每个项目都有「踩过的坑」表格，写明现象、根因、修复
2. **不留假话** —— 每个项目都有「已知限制」，没做完的事直接写出来
3. **不堆代码** —— 只有三个项目，每个都能独立跑起来

---

## 说明

- 代码里的 API Key 一律从环境变量读取，仓库中不含任何密钥
- 个人数据（`mood.txt`、`run.log`）已通过 `.gitignore` 排除，不进入版本库
