# 🏦 Transaction Dispute Assistant — MCP Server + Banking Agent

A complete **MCP (Model Context Protocol) server** and **banking agent** that enables customers to investigate suspicious transactions and file disputes through a conversational interface.

The agent is built with **LangChain / LangGraph** (ReAct loop) and connects to the MCP server over stdio transport.

---

## Use Case

| Attribute | Detail |
|---|---|
| **Scenario** | A bank customer notices an unrecognized charge and wants to file a dispute. |
| **Users** | Retail banking customers contacting support via chat. |
| **Objective** | Verify the customer, display recent transactions, confirm the disputed item, and create a dispute case — without exposing raw PII. |
| **Inputs** | Customer ID, transaction ID (selected from a list), reason for dispute. |
| **Outputs** | Dispute case ID, case status, next-step guidance. |

---

## Architecture

```
┌──────────────────────────┐       stdio / MCP        ┌─────────────────────────┐
│  Banking Agent           │ ◄──── MCP Protocol ────► │  Banking MCP Server     │
│                          │                           │                         │
│  LangGraph ReAct loop    │   list_tools              │  get_customer_profile   │
│  LangChain ChatOpenAI    │   call_tool ──────────►   │  list_transactions      │
│  Groq (llama-3.1-8b)     │   ◄────── result ──────   │  get_transaction_detail │
│                          │                           │  create_dispute_case    │
└──────────────────────────┘                           │  get_dispute_status     │
        ▲                                              └─────────────────────────┘
        │ chat
        ▼
   [Customer]
```

### Key components

| File | Role |
|---|---|
| `agent/banking_agent.py` | `BankingAgent` class — LangGraph ReAct loop + MCP tool discovery |
| `agent/executor.py` | `BankingAgentExecutor` — runtime config overrides |
| `agent/utils/basic_agent.py` | `create_basic_agent()` factory — compiles the LangGraph agent |
| `agent/utils/mcp_tools.py` | Wraps MCP tools as LangChain `BaseTool` objects |
| `agent/prompts.py` | System prompt & escalation message |
| `agent/config.py` | Env var loading with defaults |
| `mcp_server/server.py` | MCP server with 5 tool definitions |
| `mcp_server/data.py` | Synthetic customer / transaction / dispute data |

---

## MCP Tools

| # | Tool | Description |
|---|------|-------------|
| 1 | `get_customer_profile` | Look up a customer by ID. Returns masked PII, account status, KYC, risk tier. |
| 2 | `list_transactions` | Retrieve recent transactions for a customer (newest first). |
| 3 | `get_transaction_detail` | Full details of a single transaction (merchant, amount, channel, status). |
| 4 | `create_dispute_case` | Open a dispute case with a reason and optional disputed amount. |
| 5 | `get_dispute_status` | Check the current status of a dispute case by case ID. |

---

## Quick Start

### 1. Set up environment

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
```

### 2. Configure credentials

```bash
cp .env.example .env
```

Edit `.env` and set your **Groq API key** (free at [console.groq.com](https://console.groq.com)):

```env
GROQ_API_KEY=gsk_...
LLM_MODEL=llama-3.1-8b-instant
LLM_BASE_URL=https://api.groq.com/openai/v1
```

### 3. Run the smoke test (no API key needed)

```bash
python test_server.py
```

This starts the MCP server, calls every tool, and validates JSON responses.

### 4. Run the interactive agent

```bash
python -m agent
```

---

## Docker

### Build

```bash
docker build -t banking-agent .
```

### Run

```bash
# --env-file injects credentials; -it is required for interactive CLI input
docker run -it --env-file .env banking-agent
```

---

## Sample Conversation

```
🏦  Banking Dispute Agent
==================================================
Connecting to banking services …

✅  Connected. Available tools: get_customer_profile, list_transactions,
    get_transaction_detail, create_dispute_case, get_dispute_status

You: Hi, I'd like to dispute a transaction.

Agent: Of course! Could you please provide your Customer ID?
       (e.g. CUST-1001)

You: CUST-1001

Agent: Hello Jane! I've verified your account (Checking, ****-7890).
  Here are your recent transactions:

  1. TXN-50001 — $124.99 at ElectroMart Online (Electronics)
  2. TXN-50002 — $45.00 at GreenLeaf Grocery (Groceries)
  3. TXN-50003 — $299.99 at Unknown Merchant XZ9 (Uncategorized)

  Which transaction would you like to dispute?

You: TXN-50003 — I don't recognize that merchant.

Agent: Your dispute has been filed!
  • Case ID: DSP-A1B2C3D4
  • Status: Open
  • Disputed amount: $299.99

  Our team will review within 5–10 business days.

You: quit
Goodbye! Thank you for contacting Acme Bank.
```

---

## Configuration

| Variable | Default | Description |
|---|---|---|
| `GROQ_API_KEY` | *(required)* | Groq API key — free at [console.groq.com](https://console.groq.com) |
| `LLM_MODEL` | `llama-3.1-8b-instant` | Model name (any OpenAI-compatible provider works) |
| `LLM_BASE_URL` | `https://api.groq.com/openai/v1` | API base URL — swap to use OpenRouter, Azure, etc. |
| `LLM_TEMPERATURE` | `0.1` | Sampling temperature |
| `LLM_MAX_TOKENS` | `1024` | Max output tokens per turn |
| `LOG_LEVEL` | `WARNING` | Logging verbosity: `DEBUG` / `INFO` / `WARNING` / `ERROR` |

> **Switching providers** — only `.env` changes are needed. The agent uses the OpenAI-compatible API format so Groq, OpenRouter, Azure OpenAI, and others all work with zero code changes.

---

## Project Structure

```
aiw/
├── mcp_server/
│   ├── __init__.py          # Package marker
│   ├── __main__.py          # python -m mcp_server entry point
│   ├── server.py            # MCP server + 5 tool definitions
│   ├── data.py              # Synthetic customers, transactions, disputes
│   └── validators.py        # Input validation helpers
├── agent/
│   ├── __init__.py          # Exports BankingAgent, BankingAgentExecutor
│   ├── __main__.py          # python -m agent entry point
│   ├── banking_agent.py     # BankingAgent class (LangGraph ReAct + MCP)
│   ├── executor.py          # BankingAgentExecutor (runtime overrides)
│   ├── config.py            # Env var loading with defaults
│   ├── prompts.py           # System prompt & escalation message
│   └── utils/
│       ├── __init__.py
│       ├── basic_agent.py   # create_basic_agent() — LangGraph factory
│       └── mcp_tools.py     # MCP → LangChain tool adapter
├── Dockerfile               # Non-root devengine user, python:3.11-slim
├── .dockerignore
├── .env.example             # Template — copy to .env and fill in secrets
├── mcp_config.json          # MCP client config for Cursor / Claude Desktop
├── test_server.py           # MCP server smoke test (no API key needed)
├── requirements.txt         # Python dependencies
└── README.md
```

---

## Guardrails & Safety

| Rule | Implementation |
|------|----------------|
| **PII masking** | All customer data is pre-masked in the data layer. |
| **No fabrication** | Agent only uses data returned by MCP tools. |
| **Escalation triggers** | Keywords like "fraud", "identity theft", "police", or "speak to a person" trigger escalation. |
| **Amount threshold** | Disputes over $5,000 are flagged for human review. |
| **Scope limitation** | Agent only handles transaction inquiries and disputes. |
| **Frozen accounts** | Agent stops and directs to a human agent if account is frozen. |

---

## License

This project uses synthetic data only and is intended for demonstration purposes.
