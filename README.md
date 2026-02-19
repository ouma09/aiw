# 🏦 Transaction Dispute Assistant — MCP Server + Banking Agent

A complete **MCP (Model Context Protocol) server** and **banking agent** that enables customers to investigate suspicious transactions and file disputes through a conversational interface.

---

## Use Case: Transaction Dispute Assistant

| Attribute | Detail |
|---|---|
| **Scenario** | A bank customer notices an unrecognized charge on their account and wants to file a dispute. |
| **Users** | Retail banking customers contacting support via chat. |
| **Objective** | Verify the customer, display recent transactions, confirm the disputed item, and create a dispute case — all without exposing raw PII. |
| **Inputs** | Customer ID, transaction ID (selected from a list), reason for dispute. |
| **Outputs** | Dispute case ID, case status, next-step guidance. |
| **Success criteria** | The agent completes the full dispute flow end-to-end using only MCP tools and returns a valid case ID. |

---

## Architecture

```
┌──────────────┐       stdio / SSE        ┌─────────────────────────┐
│  Banking     │ ◄──── MCP Protocol ────► │  Banking MCP Server     │
│  Agent       │                          │                         │
│  (OpenAI     │   list_tools             │  get_customer_profile   │
│   + MCP      │   call_tool ──────────►  │  list_transactions      │
│   Client)    │   ◄────── result ──────  │  get_transaction_detail │
│              │                          │  create_dispute_case    │
└──────────────┘                          │  get_dispute_status     │
       ▲                                  └─────────────────────────┘
       │ chat                                      │
       ▼                                    Synthetic Data
  [Customer]                               (no real PII)
```

---

## MCP Tools

| # | Tool | Description |
|---|------|-------------|
| 1 | `get_customer_profile` | Look up a customer by ID. Returns masked PII, account status, KYC status, risk tier. |
| 2 | `list_transactions` | Retrieve recent transactions for a customer (newest first, configurable limit). |
| 3 | `get_transaction_detail` | Get full details of a single transaction (merchant, amount, channel, status). |
| 4 | `create_dispute_case` | Open a dispute case for a transaction with a reason and optional disputed amount. |
| 5 | `get_dispute_status` | Check the current status of a dispute case by case ID. |

---

## Quick Start

### 1. Install dependencies

```bash
cd aiw
pip install -r requirements.txt
```

### 2. Run the smoke test (no API key needed)

```bash
python test_server.py
```

This starts the MCP server, calls every tool, and validates JSON responses.

### 3. Run the interactive agent

```bash
# Set your OpenRouter API key (get one at https://openrouter.ai/keys)
set OPENROUTER_API_KEY=sk-or-...          # Windows
export OPENROUTER_API_KEY=sk-or-...       # Linux/Mac

# Start the agent (uses openai/gpt-4o-mini via OpenRouter by default)
python -m agent
```

### 4. Connect as an MCP server in Cursor / Claude Desktop

Copy `mcp_config.json` into your MCP client configuration. The server runs via `python -m mcp_server.server`.

---

## Example Payloads

### `get_customer_profile`

**Request:**
```json
{ "customer_id": "CUST-1001" }
```

**Response:**
```json
{
  "customer_id": "CUST-1001",
  "first_name": "Jane",
  "last_name": "D██",
  "email": "j***e@example.com",
  "phone": "***-***-4521",
  "account_number": "****-****-****-7890",
  "account_type": "Checking",
  "status": "Active",
  "kyc_status": "Verified",
  "risk_tier": "Low",
  "opened_date": "2021-03-15"
}
```

### `list_transactions`

**Request:**
```json
{ "customer_id": "CUST-1001", "limit": 3 }
```

**Response:**
```json
{
  "customer_id": "CUST-1001",
  "transactions": [
    {
      "transaction_id": "TXN-50001",
      "date": "2026-02-18T...",
      "amount": -124.99,
      "currency": "USD",
      "merchant": "ElectroMart Online",
      "category": "Electronics",
      "status": "Settled",
      "channel": "Online",
      "description": "Wireless headphones purchase"
    }
  ]
}
```

### `create_dispute_case`

**Request:**
```json
{
  "customer_id": "CUST-1001",
  "transaction_id": "TXN-50003",
  "reason": "I did not make this purchase. The merchant is unknown to me."
}
```

**Response:**
```json
{
  "case_id": "DSP-A1B2C3D4",
  "customer_id": "CUST-1001",
  "transaction_id": "TXN-50003",
  "merchant": "Unknown Merchant XZ9",
  "original_amount": -299.99,
  "disputed_amount": 299.99,
  "currency": "USD",
  "reason": "I did not make this purchase. The merchant is unknown to me.",
  "status": "Open",
  "created_at": "2026-02-19T...",
  "resolution": null,
  "notes": "Case opened via dispute assistant. Under review."
}
```

---

## Sample Agent Conversation

```
🏦  Acme Bank — Transaction Dispute Assistant
==================================================
Connected. Available tools: get_customer_profile, list_transactions,
  get_transaction_detail, create_dispute_case, get_dispute_status

You: Hi, I'd like to dispute a transaction. My ID is CUST-1001.

  🔧 Calling get_customer_profile({"customer_id": "CUST-1001"}) …
  🔧 Calling list_transactions({"customer_id": "CUST-1001"}) …

Agent: Hello Jane! I've verified your account (Checking, ****-7890).
  Here are your recent transactions:

  1. TXN-50001 — $124.99 at ElectroMart Online (Electronics)
  2. TXN-50002 — $45.00 at GreenLeaf Grocery (Groceries)
  3. TXN-50003 — $299.99 at Unknown Merchant XZ9 (Uncategorized)
  4. TXN-50004 — +$2,500.00 Employer Direct Deposit
  5. TXN-50005 — $89.50 at CloudFit Gym (Health & Fitness)

  Which transaction would you like to dispute?

You: TXN-50003 — I don't recognize that merchant at all.

  🔧 Calling get_transaction_detail({"customer_id":"CUST-1001",
       "transaction_id":"TXN-50003"}) …

Agent: Here are the details for TXN-50003:
  • Amount: $299.99
  • Merchant: Unknown Merchant XZ9
  • Channel: Online
  • Date: Feb 14, 2026
  • Status: Settled

  I'd like to file a dispute for this transaction.
  Can you briefly describe why you believe this charge is incorrect?

You: I never made this purchase. I don't know this merchant.

  🔧 Calling create_dispute_case({"customer_id":"CUST-1001",
       "transaction_id":"TXN-50003",
       "reason":"Customer did not make this purchase. Merchant unrecognized."}) …

Agent: Your dispute has been filed successfully!
  • Case ID: DSP-A1B2C3D4
  • Status: Open
  • Disputed amount: $299.99

  Our team will review your case within 5–10 business days.
  You can check the status anytime by providing your case ID.
  Is there anything else I can help you with?

You: quit
Goodbye! Thank you for contacting Acme Bank.
```

---

## Guardrails & Safety

| Rule | Implementation |
|------|---------------|
| **PII masking** | All customer data is pre-masked in the data layer. Names, emails, phones, and account numbers are redacted. |
| **No data fabrication** | The agent only uses data returned by MCP tools. The system prompt explicitly prohibits guessing. |
| **Escalation triggers** | Keywords like "fraud", "identity theft", "police", or "speak to a person" trigger immediate escalation to a human agent. |
| **Amount threshold** | Disputes over $5,000 are flagged for human review. |
| **Scope limitation** | The agent only handles transaction inquiries and disputes. Off-topic requests are politely declined. |
| **Frozen accounts** | If account status is "Frozen", the agent stops and directs the customer to a human agent. |

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
│   ├── __init__.py          # Package marker
│   ├── __main__.py          # python -m agent entry point
│   ├── banking_agent.py     # Interactive agent loop (OpenAI + MCP client)
│   ├── config.py            # Environment & model configuration
│   └── prompts.py           # System prompt & escalation templates
├── mcp_config.json          # MCP client configuration for Cursor/Claude
├── test_server.py           # Standalone smoke test (no API key needed)
├── requirements.txt         # Python dependencies
├── README.md                # This file
└── DEMO_SCRIPT.md           # 2–3 minute demo walkthrough
```

---

## Configuration

| Environment variable | Default | Description |
|---|---|---|
| `OPENROUTER_API_KEY` | *(required)* | OpenRouter API key ([get one here](https://openrouter.ai/keys)) |
| `LLM_MODEL` | `openai/gpt-4o-mini` | Model to use via OpenRouter (e.g. `anthropic/claude-3.5-sonnet`, `google/gemini-2.0-flash`) |
| `LLM_BASE_URL` | `https://openrouter.ai/api/v1` | LLM API base URL |
| `LLM_TEMPERATURE` | `0.1` | Sampling temperature |
| `LLM_MAX_TOKENS` | `1024` | Max output tokens per turn |

---

## License

This project uses synthetic data only and is intended for demonstration purposes.

