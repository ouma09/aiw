# Demo Script — Transaction Dispute Assistant (2–3 minutes)

## Setup (before demo)

1. Dependencies installed: `pip install -r requirements.txt`
2. `OPENROUTER_API_KEY` set in the environment.
3. Terminal open in the `aiw/` directory.

---

## Demo Flow

### Slide 1 — Introduction (30 sec)

> "We built a **Transaction Dispute Assistant** using MCP. It has two
> components: an MCP server with 5 banking tools and an agent that
> orchestrates them to resolve disputes end-to-end."

- Show the architecture diagram from the README.

---

### Slide 2 — MCP Server Smoke Test (30 sec)

> "First, let's prove the MCP server works. This test starts the
> server, calls every tool, and validates JSON responses."

```bash
python test_server.py
```

**What to point out:**
- 5 tools discovered automatically.
- `get_customer_profile` returns masked PII (no real data leaks).
- `create_dispute_case` returns a valid case ID.
- Duplicate disputes are caught.
- All tests pass ✅.

---

### Slide 3 — Live Agent Conversation (90 sec)

> "Now let's run the full agent. It connects to the MCP server,
> discovers the tools, and chats with the user."

```bash
python -m agent
```

**Conversation to type:**

1. **You:** `Hi, I'd like to dispute a charge. My customer ID is CUST-1001.`

   → *Agent calls `get_customer_profile` and `list_transactions`,
     then displays the customer's recent activity.*

2. **You:** `TXN-50003 looks suspicious — I don't recognize that merchant.`

   → *Agent calls `get_transaction_detail` and shows full details
     of the $299.99 charge from "Unknown Merchant XZ9".*

3. **You:** `I never made this purchase. Please file a dispute.`

   → *Agent calls `create_dispute_case` and returns a case ID
     (e.g., DSP-A1B2C3D4) with status "Open".*

4. **You:** `quit`

**What to point out:**
- The agent only uses data from MCP tool responses (no fabrication).
- PII is masked in every output.
- The dispute case was created end-to-end.

---

### Slide 4 — Safety & Guardrails (30 sec)

> "The agent has built-in guardrails."

**Quick demo — type in a new session:**

1. **You:** `I think someone stole my identity`

   → *Agent immediately triggers escalation, no tool calls.*
   → *Shows: "I'm connecting you to a specialist …"*

2. **(Explain):** Frozen accounts, high amounts (>$5k), and distress
   keywords all trigger human escalation.

---

### Closing (15 sec)

> "In summary: 5 MCP tools, full dispute flow, PII masking,
> escalation guardrails, and all built on synthetic data.
> Everything is in the repo — README, smoke tests, and this demo script."

---

## Troubleshooting

| Issue | Fix |
|---|---|
| `ModuleNotFoundError: mcp` | Run `pip install -r requirements.txt` |
| `OPENROUTER_API_KEY` error | Set the env variable: `set OPENROUTER_API_KEY=sk-or-...` |
| Server hangs | Ensure Python ≥ 3.10 is on PATH |
| Tool returns error JSON | Check the customer/transaction ID format in data.py |

