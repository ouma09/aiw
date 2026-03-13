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

# Types for which the LLM sometimes sends a string instead of a number.
# Using Union[numeric, str] makes Groq's schema validation accept both.
_NUMERIC_TYPES = {"number", "integer"}


def _build_args_schema(schema: dict) -> type | None:
    """
    Convert a JSON Schema object into a Pydantic model class that LangChain
    can use as args_schema. This is what tells the LLM the correct parameter
    names and types for each tool call.

    Numeric fields (number / integer) accept Union[numeric, str] so that
    Groq's request validation passes even when the LLM emits a quoted number
    like "299.99" instead of the bare literal 299.99.
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

        # Allow numeric fields to also accept str — the LLM occasionally
        # sends numbers as quoted strings; we coerce them in _acall.
        if json_type in _NUMERIC_TYPES:
            python_type = typing.Union[python_type, str]  # type: ignore[assignment]

        if name in required:
            fields[name] = (python_type, Field(..., description=description))
        else:
            fields[name] = (
                typing.Optional[python_type],
                Field(default=None, description=description),
            )

    return create_model("ToolArgs", **fields)


def _coerce_numerics(kwargs: dict[str, Any], schema: dict) -> dict[str, Any]:
    """Cast string values to the numeric type the MCP tool actually expects."""
    properties = schema.get("properties", {})
    result: dict[str, Any] = {}
    for k, v in kwargs.items():
        jtype = properties.get(k, {}).get("type")
        if isinstance(v, str):
            if jtype == "number":
                try:
                    v = float(v)
                except (ValueError, TypeError):
                    pass
            elif jtype == "integer":
                try:
                    v = int(v)
                except (ValueError, TypeError):
                    pass
        result[k] = v
    return result


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
        # Strip Nones then coerce string-encoded numbers to the right type
        filtered = {k: v for k, v in kwargs.items() if v is not None}
        filtered = _coerce_numerics(filtered, schema)
        result = await session.call_tool(name, arguments=filtered)
        return _format_tool_result(result)

    def _call(**kwargs: Any) -> str:
        import asyncio
        import concurrent.futures
        # Strip Nones then coerce string-encoded numbers to the right type
        filtered = {k: v for k, v in kwargs.items() if v is not None}
        filtered = _coerce_numerics(filtered, schema)
        loop = asyncio.get_event_loop()
        if loop.is_running():
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, _acall(**filtered))
                return future.result()
        return loop.run_until_complete(_acall(**filtered))

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
