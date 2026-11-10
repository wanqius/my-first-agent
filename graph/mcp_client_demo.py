"""MCP 客户端：连上 mcp_server.py，先问它有哪些工具，再调一个。

运行：
    .venv\\Scripts\\python.exe graph\\mcp_client_demo.py
"""

import asyncio
import sys

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

SERVER = StdioServerParameters(
    command=sys.executable,               # 用当前这个 venv 的 python
    args=["graph/mcp_server.py"],         # 拉起 server
)


async def main():
    async with stdio_client(SERVER) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # ① 问：你有哪些工具？（不需要知道 server 是怎么写的）
            tools = await session.list_tools()
            print("可用工具：")
            for t in tools.tools:
                print(f"  - {t.name}: {t.description}")
                print(f"    参数 schema: {t.input_schema}")

            # ② 调：用工具名 + 参数字典
            result = await session.call_tool("get_today", {})
            print("\n调用 get_today →", result.content)

            result2 = await session.call_tool("count_words", {"text": "今天 心情 很好"})
            print("调用 count_words →", result2.content)


if __name__ == "__main__":
    asyncio.run(main())
