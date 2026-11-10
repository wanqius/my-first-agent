"""最小的 MCP Server：通过标准协议对外暴露工具。

启动方式（默认 stdio，由客户端拉起）：
    .venv\\Scripts\\python.exe graph\\mcp_server.py
"""

import datetime

from mcp.server.mcpserver import MCPServer

server = MCPServer("my-tools")


@server.tool()
def get_today() -> str:
    """查询今天的日期，格式 YYYY-MM-DD。不需要参数。"""
    return datetime.date.today().isoformat()


@server.tool()
def count_words(text: str) -> int:
    """统计一段文字有多少个字符（含空格）。需要参数 text。"""
    return len(text)

@server.tool()
def count_chars(text: str) -> int:
    """统计一段文字的字符数（不含空格）。需要参数 text。"""
    return len(text.replace(" ", ""))


if __name__ == "__main__":
    server.run()  # 默认 stdio
