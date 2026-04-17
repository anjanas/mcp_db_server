"""
Tests for MCP server tool registration and error handling.

`get_overdue_invoices_over_1000` is defined in mcp_server.py but commented out — it must
not be callable via the MCP surface.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mcp.server.fastmcp.exceptions import ToolError

import mcp_server


# Tool name that appears commented out in mcp_server.py (not registered with @mcp.tool).
NON_EXPOSED_TOOL = "get_overdue_invoices_over_1000"


@pytest.mark.asyncio
async def test_call_tool_unknown_name_raises():
    """Calling a tool that was never registered fails with ToolError."""
    with pytest.raises(ToolError, match=f"Unknown tool: {NON_EXPOSED_TOOL}"):
        await mcp_server.mcp.call_tool(NON_EXPOSED_TOOL, {})


@pytest.mark.asyncio
async def test_non_exposed_tool_not_in_list_tools():
    """Commented-out tools do not appear in tools/list."""
    tools = await mcp_server.mcp.list_tools()
    names = {t.name for t in tools}
    assert NON_EXPOSED_TOOL not in names
    # Sanity: real tools from mcp_server.py are present
    assert "list_all_invoices" in names
    assert "get_customer_by_id" in names
