"""
Banking Agent — Transaction Dispute Assistant

This agent connects to the Banking MCP Server, discovers available tools,
and runs an interactive conversation loop with the user to handle
transaction disputes end-to-end.

Usage:
    python -m agent.banking_agent
"""

import asyncio
import json
import sys
import os

# Force UTF-8 output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# Ensure project root is on the path so we can import sibling packages
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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
    MAX_DISPUTE_AMOUNT_AUTO,
)

try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None  # type: ignore


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _needs_escalation(user_msg: str) -> bool:
    """Check if the user message contains escalation trigger words."""
    lower = user_msg.lower()
    return any(kw in lower for kw in ESCALATION_KEYWORDS)


def _format_tool_result(result) -> str:
    """Extract text content from an MCP CallToolResult."""
    parts = []
    for block in result.content:
        if hasattr(block, "text"):
            parts.append(block.text)
    return "\n".join(parts)


def _build_openai_tools(mcp_tools) -> list[dict]:
    """Convert MCP tool definitions to OpenAI function-calling format."""
    oai_tools = []
    for t in mcp_tools:
        schema = t.inputSchema if hasattr(t, "inputSchema") else {}
        oai_tools.append(
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description or "",
                    "parameters": schema,
                },
            }
        )
    return oai_tools


# ---------------------------------------------------------------------------
# Agent loop
# ---------------------------------------------------------------------------

async def run_agent():
    """Main agent loop: connect to MCP server, then chat with user."""

    if AsyncOpenAI is None:
        print(
            "ERROR: 'openai' package is required. Install it with:\n"
            "  pip install openai",
            file=sys.stderr,
        )
        sys.exit(1)

    if not LLM_API_KEY:
        print(
            "ERROR: Set the OPENROUTER_API_KEY environment variable.\n"
            "  Get your key at https://openrouter.ai/keys",
            file=sys.stderr,
        )
        sys.exit(1)

    llm = AsyncOpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)

    server_params = StdioServerParameters(
        command=MCP_SERVER_COMMAND,
        args=MCP_SERVER_ARGS,
        env={**os.environ},
    )

    print("🏦  Acme Bank — Transaction Dispute Assistant")
    print("=" * 50)
    print("Connecting to banking services …\n")

    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            # Discover tools
            tools_result = await session.list_tools()
            mcp_tools = tools_result.tools
            oai_tools = _build_openai_tools(mcp_tools)

            tool_names = [t.name for t in mcp_tools]
            print(f"✅  Connected. Available tools: {', '.join(tool_names)}\n")
            print("Type your message below (or 'quit' to exit).\n")

            messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]

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

                # Escalation check
                if _needs_escalation(user_input):
                    print(
                        f"\nAgent: {ESCALATION_MESSAGE.format(ref_id='your Customer ID')}\n"
                    )
                    continue

                messages.append({"role": "user", "content": user_input})

                # ---- LLM call (with tool use loop) ----
                while True:
                    response = await llm.chat.completions.create(
                        model=LLM_MODEL,
                        messages=messages,
                        tools=oai_tools if oai_tools else None,
                        temperature=LLM_TEMPERATURE,
                        max_tokens=LLM_MAX_TOKENS,
                    )

                    choice = response.choices[0]
                    msg = choice.message

                    # If the model wants to call tool(s)
                    if msg.tool_calls:
                        # Append the assistant message with tool_calls
                        messages.append(msg.model_dump())

                        for tc in msg.tool_calls:
                            fn_name = tc.function.name
                            fn_args = json.loads(tc.function.arguments)

                            print(f"  🔧 Calling {fn_name}({json.dumps(fn_args)}) …")

                            # Call the MCP tool
                            try:
                                result = await session.call_tool(
                                    fn_name, arguments=fn_args
                                )
                                tool_output = _format_tool_result(result)
                            except Exception as exc:
                                tool_output = json.dumps(
                                    {"error": f"Tool call failed: {exc}"}
                                )

                            messages.append(
                                {
                                    "role": "tool",
                                    "tool_call_id": tc.id,
                                    "content": tool_output,
                                }
                            )
                        # Loop back to let the model process tool results
                        continue

                    # Normal text response — print and break inner loop
                    assistant_text = msg.content or ""
                    messages.append({"role": "assistant", "content": assistant_text})
                    print(f"\nAgent: {assistant_text}\n")
                    break


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    asyncio.run(run_agent())


if __name__ == "__main__":
    main()

