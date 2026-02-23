"""
MCP tools adapter — wrap MCP server tools as LangChain tools.

Given an MCP ClientSession and the result of list_tools(), builds a list of
LangChain-compatible tools that delegate to session.call_tool() so the
LangGraph agent can use them in the ReAct loop.
"""

from __future__ import annotations

import typing
from typing import Any, Sequence

from langchain_core.tools import BaseTool, StructuredTool
from pydantic import create_model, Field

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp import ClientSession


# ---------------------------------------------------------------------------
# JSON Schema → Pydantic model
# ---------------------------------------------------------------------------

_JSON_TYPE_MAP: dict[str, type] = {
    "string": str,
    "integer": int,
    "number": float,
    "boolean": bool,
    "array": list,
    "object": dict,
}


def _build_args_schema(schema: dict) -> type | None:
    """
    Convert a JSON Schema object into a Pydantic model class that LangChain
    can use as args_schema. This is what tells the LLM the correct parameter
    names and types for each tool call.
    """
    properties: dict = schema.get("properties", {})
    required: list[str] = schema.get("required", [])

    if not properties:
        return None

    fields: dict[str, Any] = {}
    for name, prop in properties.items():
        json_type = prop.get("type", "string")
        python_type = _JSON_TYPE_MAP.get(json_type, str)
        description = prop.get("description", "")

        if name in required:
            fields[name] = (python_type, Field(..., description=description))
        else:
            fields[name] = (
                typing.Optional[python_type],
                Field(default=None, description=description),
            )

    return create_model("ToolArgs", **fields)


# ---------------------------------------------------------------------------
# Tool factory
# ---------------------------------------------------------------------------

def _format_tool_result(result: Any) -> str:
    """Extract text content from an MCP CallToolResult."""
    parts = []
    for block in result.content:
        if hasattr(block, "text"):
            parts.append(block.text)
    return "\n".join(parts)


def _make_tool_spec(mcp_tool: Any, session: "ClientSession") -> BaseTool:
    """Build a single LangChain tool that calls one MCP tool via session.call_tool."""

    name = mcp_tool.name
    description = mcp_tool.description or ""
    schema = getattr(mcp_tool, "inputSchema", None) or {}
    args_schema = _build_args_schema(schema)

    async def _acall(**kwargs: Any) -> str:
        result = await session.call_tool(name, arguments=kwargs)
        return _format_tool_result(result)

    def _call(**kwargs: Any) -> str:
        import asyncio
        import concurrent.futures
        loop = asyncio.get_event_loop()
        if loop.is_running():
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, _acall(**kwargs))
                return future.result()
        return loop.run_until_complete(_acall(**kwargs))

    return StructuredTool.from_function(
        name=name,
        description=description,
        func=_call,
        coroutine=_acall,
        args_schema=args_schema,  # ← proper Pydantic schema so LLM formats calls correctly
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_langchain_tools_from_mcp(
    session: "ClientSession",
    mcp_tools: Sequence[Any],
) -> list[BaseTool]:
    """
    Convert MCP tool definitions to LangChain BaseTool list.

    Args:
        session: Active MCP ClientSession used to call tools.
        mcp_tools: Iterable of MCP Tool objects (e.g. from list_tools().tools).

    Returns:
        List of LangChain tools that delegate to session.call_tool.
    """
    return [_make_tool_spec(t, session) for t in mcp_tools]
