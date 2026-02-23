"""
BankingLangchainAgentExecutor
=============================
Mirrors the blueprint's BasicLangchainAgentExecutor but **without** the A2A /
AI-Workbench framework.  Useful if you later want to wrap the agent in a
lightweight web API (FastAPI / uvicorn) while keeping the executor pattern.

For normal CLI use, simply call BankingAgent.run() from banking_agent.py.
"""

from __future__ import annotations

import logging
import sys
from typing import List

from agent.banking_agent import BankingAgent
from agent.config import (
    LLM_API_KEY,
    LLM_BASE_URL,
    LLM_MODEL,
    LLM_TEMPERATURE,
    LLM_MAX_TOKENS,
)
from agent.prompts import SYSTEM_PROMPT

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.propagate = False

_console_handler = logging.StreamHandler(sys.stdout)
_console_handler.setFormatter(
    logging.Formatter("AgentExecutor | {message}", style="{")
)
logger.addHandler(_console_handler)


class BankingAgentExecutor:
    """
    Thin orchestration wrapper around BankingAgent.

    Follows the blueprint's executor pattern:
      - Holds a configured BankingAgent instance.
      - `_get_executing_agent(metadata)` allows runtime config overrides
        (model, system prompt, recursion limit) via a metadata dict.
      - `execute()` is the main entry point — runs the interactive loop.

    Metadata override keys (all optional):
        llm_model       (str)
        llm_temperature (float)
        llm_max_tokens  (int)
        system_message  (str)
        recursion_limit (int)
        name            (str)
    """

    def __init__(
        self,
        agent: BankingAgent | None = None,
    ) -> None:
        self.agent = agent or BankingAgent(
            llm_api_key=LLM_API_KEY,
            llm_base_url=LLM_BASE_URL,
            llm_model=LLM_MODEL,
            llm_temperature=LLM_TEMPERATURE,
            llm_max_tokens=LLM_MAX_TOKENS,
            system_message=SYSTEM_PROMPT,
        )

    def _get_executing_agent(self, metadata: dict | None = None) -> BankingAgent:
        """
        Return either the default agent or a new one with settings overridden
        from the metadata dict. Mirrors blueprint's _get_executing_agent().
        """
        if not metadata:
            logger.info("Using default agent settings.")
            return self.agent

        logger.info("Applying runtime overrides from metadata: %s", list(metadata.keys()))

        def _override(field: str, default):
            val = metadata.get(field)
            if val is not None and val != default:
                logger.info("Override '%s': %r → %r", field, default, val)
            return val if val is not None else default

        return BankingAgent(
            name=_override("name", self.agent.name),
            system_message=_override("system_message", self.agent.system_message),
            llm_api_key=LLM_API_KEY,
            llm_base_url=LLM_BASE_URL,
            llm_model=_override("llm_model", LLM_MODEL),
            llm_temperature=float(_override("llm_temperature", LLM_TEMPERATURE)),
            llm_max_tokens=int(_override("llm_max_tokens", LLM_MAX_TOKENS)),
            recursion_limit=int(_override("recursion_limit", self.agent.recursion_limit)),
        )

    async def execute(self, metadata: dict | None = None) -> None:
        """Run the interactive CLI conversation loop."""
        agent = self._get_executing_agent(metadata)
        await agent.run()
