"""把 Agent 包成 HTTP 接口。

启动：
    .venv\\Scripts\\python.exe graph\\api_server.py
    # 或：.venv\\Scripts\\python.exe -m uvicorn graph.api_server:app --port 8000

调用：
    curl http://127.0.0.1:8000/health
    curl -X POST http://127.0.0.1:8000/chat -H "Content-Type: application/json" -d "{\"question\":\"今天几号？\"}"
"""

import asyncio
import os
import sys
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from pydantic import BaseModel, Field

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent_core import run_agent  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动时连一次 MCP，整个服务生命周期共用这条连接。"""
    params = StdioServerParameters(command=sys.executable, args=[os.path.join(HERE, "mcp_server.py")])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()

            app.state.session = session
            app.state.tools = [t.name for t in tools.tools]
            app.state.tools_text = "\n".join(f"- {t.name}: {t.description}" for t in tools.tools)
            app.state.lock = asyncio.Lock()   # 一条连接，多个请求要排队

            print(f"[startup] MCP 已连接，工具: {app.state.tools}", flush=True)
            yield
    print("[shutdown] MCP 连接已关闭", flush=True)


app = FastAPI(title="My First Agent API", version="0.1.0", lifespan=lifespan)


class ChatIn(BaseModel):
    question: str = Field(..., min_length=1, max_length=500, description="用户问题")


class ChatOut(BaseModel):
    answer: str
    calls: list[str]
    elapsed_ms: int


@app.get("/health")
async def health():
    return {"status": "ok", "tools": app.state.tools}


@app.get("/", include_in_schema=False)
async def index():
    return FileResponse(os.path.join(HERE, "web", "index.html"), media_type="text/html")


@app.post("/chat", response_model=ChatOut)
async def chat(body: ChatIn):
    t0 = time.perf_counter()
    async with app.state.lock:
        r = await run_agent(body.question, session=app.state.session, tools_text=app.state.tools_text)
    if r["error"]:
        raise HTTPException(status_code=502, detail="模型调用失败")
    return ChatOut(
        answer=r["answer"],
        calls=r["calls"],
        elapsed_ms=int((time.perf_counter() - t0) * 1000),
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
