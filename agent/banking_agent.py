"""
Banking Agent — Transaction Dispute Assistant (LangChain/LangGraph rewrite)

Architecture (mirrors the langchain_blueprint):
  ┌─────────────────┐
  │  BankingAgent   │  ← this file
  │                 │
  │  _get_tools()   │  ← discovers tools from MCP server (stdio or HTTP)
  │  run()          │  ← interactive CLI loop powered by LangGraph ReAct
  └─────────────────┘

The MCP server is launched as a subprocess (stdio transport) just like before,
but tool execution is now handled by LangGraph's ReAct loop instead of a
hand-rolled OpenAI tool-call loop.

Usage:
    python -m agent.banking_agent
"""

from __future__ import annotations

import asyncio
import os
import sys
import logging

# Force UTF-8 output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# Ensure project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx

from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langchain_openai import ChatOpenAI

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from agent.prompts import SYSTEM_PROMPT, ESCALATION_MESSAGE
from agent.config import (
    MCP_SERVER_COMMAND,
    MCP_SERVER_ARGS,
    LLM_MODEL,
    LLM_API_KEY,
    LLM_BASE_URL,
    LLM_TEMPERATURE,
    LLM_MAX_TOKENS,
    ESCALATION_KEYWORDS,
)
from agent.utils.mcp_tools import build_langchain_tools_from_mcp
from agent.utils.basic_agent import create_basic_agent

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "WARNING").upper(), logging.WARNING),
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _needs_escalation(user_msg: str) -> bool:
    """Return True when the message contains escalation trigger words."""
    lower = user_msg.lower()
    return any(kw in lower for kw in ESCALATION_KEYWORDS)


def _extract_text(messages: list[BaseMessage]) -> str:
    """Return the text content of the last AI message in a LangGraph output."""
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and msg.content:
            return str(msg.content)
    return ""


# ---------------------------------------------------------------------------
# Agent class  (mirrors BasicLangchainAgent from the blueprint)
# ---------------------------------------------------------------------------

class BankingAgent:
    """
    Banking Dispute Agent powered by LangGraph ReAct + MCP tools.

    Follows the blueprint pattern:
      - `_get_tools(session)`  — adapter: MCP tools → LangChain tools
      - `run()`                — async CLI loop (replaces A2A stream())

    Attributes:
        name:            Human-readable agent name.
        system_message:  System prompt injected into every conversation.
        llm:             LangChain ChatModel instance.
        recursion_limit: Max LangGraph steps per turn.
    """

    SUPPORTED_CONTENT_TYPES = ["text", "text/plain"]

    def __init__(
        self,
        name: str = "Banking Dispute Agent",
        system_message: str = SYSTEM_PROMPT,
        llm_api_key: str = "",
        llm_base_url: str = "",
        llm_model: str = "",
        llm_temperature: float = 0.1,
        llm_max_tokens: int = 1024,
        recursion_limit: int = 75,
    ) -> None:
        self.name = name
        self.system_message = system_message
        self.recursion_limit = recursion_limit

        if not llm_api_key:
            raise ValueError(
                "LLM API key is required. Set GROQ_API_KEY in your .env file."
            )

        # Use verify=False to bypass SSL certificate issues on Windows /
        # corporate environments that intercept TLS traffic.
        self.llm = ChatOpenAI(
            api_key=llm_api_key,
            base_url=llm_base_url or None,
            model=llm_model,
            temperature=llm_temperature,
            max_tokens=llm_max_tokens,
            http_client=httpx.Client(verify=False),
            http_async_client=httpx.AsyncClient(verify=False),
        )

    # ------------------------------------------------------------------
    # Tool discovery  (blueprint: _get_tools)
    # ------------------------------------------------------------------

    async def _get_tools(self, session: ClientSession):
        """
        Discover available tools from the MCP server and wrap them as
        LangChain BaseTool objects.
        """
        tools_result = await session.list_tools()
        lc_tools = build_langchain_tools_from_mcp(session, tools_result.tools)
        logger.info("Discovered %d MCP tools", len(lc_tools))
        return lc_tools

    # ------------------------------------------------------------------
    # Main interactive loop  (blueprint: stream / invoke)
    # ------------------------------------------------------------------

    async def run(self) -> None:
        """
        Connect to the MCP server via stdio, then run an interactive
        LangGraph ReAct conversation loop in the terminal.
        """
        server_params = StdioServerParameters(
            command=MCP_SERVER_COMMAND,
            args=MCP_SERVER_ARGS,
            env={**os.environ},
        )

        print(f"\n🏦  {self.name}")
        print("=" * 50)
        print("Connecting to banking services …\n")

        async with stdio_client(server_params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()

                tools = await self._get_tools(session)
                tool_names = [t.name for t in tools]
                print(f"✅  Connected. Available tools: {', '.join(tool_names)}\n")
                print("Type your message below (or 'quit' to exit).\n")

                # Build the LangGraph agent (blueprint: create_basic_agent)
                agent = create_basic_agent(
                    model=self.llm,
                    tools=tools,
                    system_prompt=self.system_message,
                    recursion_limit=self.recursion_limit,
                    run_name=self.name,
                )

                # Conversation history kept as LangChain messages
                history: list[BaseMessage] = []

                while True:
                    # ---- User input ----
                    try:
                        user_input = input("You: ").strip()
                    except (EOFError, KeyboardInterrupt):
                        print("\nGoodbye!")
                        break

                    if not user_input:
                        continue
                    if user_input.lower() in ("quit", "exit", "q"):
                        print("Goodbye! Thank you for contacting Acme Bank.")
                        break

                    # Escalation guard
                    if _needs_escalation(user_input):
                        print(
                            f"\nAgent: {ESCALATION_MESSAGE.format(ref_id='your Customer ID')}\n"
                        )
                        continue

                    # ---- LangGraph invocation ----
                    history.append(HumanMessage(content=user_input))
                    exit_session = False

                    try:
                        # Small pause to stay within Groq free-tier rate limits
                        await asyncio.sleep(1)

                        # `ainvoke` runs the full ReAct loop including tool calls
                        result = await agent.ainvoke({"messages": history})

                        output_messages: list[BaseMessage] = result.get("messages", [])
                        assistant_text = _extract_text(output_messages)

                        if assistant_text:
                            history.append(AIMessage(content=assistant_text))

                        print(f"\nAgent: {assistant_text}\n")

                    except Exception as exc:
                        # Pop the user message so the turn can be retried
                        history.pop()
                        exc_str = str(exc)
                        if "429" in exc_str or "Too Many Requests" in exc_str:
                            print(
                                "\n⚠️  Rate limit reached (Groq free tier). "
                                "Please wait a few seconds and try again.\n"
                            )
                        elif "401" in exc_str or "Invalid API Key" in exc_str:
                            print("\n❌  Invalid API key. Check OPENROUTER_API_KEY in .env.\n")
                            exit_session = True
                        else:
                            logger.error("Agent error: %s", exc)
                            print(f"\n❌  An error occurred: {exc}\n")

                    if exit_session:
                        break


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    agent = BankingAgent(
        llm_api_key=LLM_API_KEY,
        llm_base_url=LLM_BASE_URL,
        llm_model=LLM_MODEL,
        llm_temperature=LLM_TEMPERATURE,
        llm_max_tokens=LLM_MAX_TOKENS,
    )
    asyncio.run(agent.run())


if __name__ == "__main__":
    main()
