"""
Agent configuration — connection settings, model parameters, etc.
Uses OpenRouter as the LLM provider (OpenAI-compatible API).
"""

import os
from dotenv import load_dotenv

# Load .env from project root
load_dotenv()

# MCP server command (used by the agent to spawn / connect to the server)
MCP_SERVER_COMMAND = os.getenv("MCP_SERVER_COMMAND", "python")
MCP_SERVER_ARGS = os.getenv(
    "MCP_SERVER_ARGS", "-m mcp_server.server"
).split()

# LLM settings — OpenRouter (OpenAI-compatible)
LLM_MODEL = os.getenv("LLM_MODEL", "llama-3.1-8b-instant")
LLM_API_KEY = os.getenv("GROQ_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.1"))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "1024"))

# Safety
MAX_DISPUTE_AMOUNT_AUTO = 5000.0  # auto-escalate above this
ESCALATION_KEYWORDS = [
    "fraud",
    "identity theft",
    "stolen",
    "police",
    "law enforcement",
    "speak to a person",
    "talk to someone",
    "human agent",
]

