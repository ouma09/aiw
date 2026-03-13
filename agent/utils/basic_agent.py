"""
basic_agent.py — LangGraph agent factory.

Creates a compiled LangGraph ReAct agent bound to a list of LangChain tools
and a system prompt. This mirrors the blueprint's `create_basic_agent()` but
uses only public packages (no private Workbench middleware).
"""

from __future__ import annotations

from typing import Any, Callable, Sequence

from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool
from langgraph.prebuilt import create_react_agent
from langgraph.graph.state import CompiledStateGraph


def create_basic_agent(
    model: BaseChatModel,
    tools: Sequence[BaseTool | Callable | dict[str, Any]],
    system_prompt: str,
    recursion_limit: int = 75,
    run_name: str = "banking_agent",
) -> CompiledStateGraph:
    """
    Build a compiled LangGraph ReAct agent.

    Args:
        model:           An instantiated LangChain chat model.
        tools:           LangChain tools the agent may call.
        system_prompt:   System message injected at the start of every conversation.
        recursion_limit: Maximum number of LangGraph steps before aborting.
        run_name:        Tag used in traces / run names.

    Returns:
        A compiled LangGraph StateGraph ready to stream/invoke.
    """
    agent = create_react_agent(
        model=model,
        tools=tools,
        prompt=system_prompt,
    )
    return agent.with_config(
        {
            "recursion_limit": recursion_limit,
            "run_name": run_name,
            "tags": [run_name],
        }
    )
