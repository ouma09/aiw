"""
Banking MCP Server — Transaction Dispute Assistant

Exposes the following tools via the Model Context Protocol:
  1. get_customer_profile  – Look up a customer by ID
  2. list_transactions     – Retrieve recent transactions for a customer
  3. get_transaction_detail – Get full details of a single transaction
  4. create_dispute_case   – Open a dispute case for a transaction
  5. get_dispute_status    – Check the status of an existing dispute

Run:
    python -m mcp_server.server          # stdio transport (default)
    python -m mcp_server.server --sse    # SSE transport (HTTP)
"""

import json
import sys
import logging
from datetime import datetime

from mcp.server.fastmcp import FastMCP

from mcp_server.data import (
    CUSTOMERS,
    TRANSACTIONS,
    DISPUTE_CASES,
    generate_case_id,
)
from mcp_server.validators import (
    validate_customer_id,
    validate_transaction_id,
    validate_dispute_id,
    validate_reason,
    validate_amount,
)

# ---------------------------------------------------------------------------
# Logging — mask PII in all log output
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("banking-mcp")

# ---------------------------------------------------------------------------
# MCP Server instance
# ---------------------------------------------------------------------------
mcp = FastMCP(
    "banking-dispute-server",
    instructions=(
        "Banking MCP server for the Transaction Dispute Assistant. "
        "Provides tools to look up customers, view transactions, "
        "and manage dispute cases. All PII is masked."
    ),
)


# ============================= TOOL 1 =====================================
@mcp.tool()
def get_customer_profile(customer_id: str) -> str:
    """
    Look up a bank customer profile by their customer ID.

    Args:
        customer_id: The unique customer identifier (format: CUST-XXXX).

    Returns:
        JSON string with masked customer profile data including account
        status, KYC status, and risk tier. PII fields are redacted.
    """
    try:
        cid = validate_customer_id(customer_id)
    except ValueError as exc:
        return json.dumps({"error": str(exc)})

    customer = CUSTOMERS.get(cid)
    if not customer:
        logger.info("Customer lookup miss: %s", cid)
        return json.dumps({"error": f"Customer {cid} not found."})

    logger.info("Customer lookup: %s", cid)
    return json.dumps(customer, indent=2)


# ============================= TOOL 2 =====================================
@mcp.tool()
def list_transactions(customer_id: str, limit: int = 10) -> str:
    """
    Retrieve the most recent transactions for a customer.

    Args:
        customer_id: The unique customer identifier (format: CUST-XXXX).
        limit: Maximum number of transactions to return (default 10, max 50).

    Returns:
        JSON array of transaction objects sorted newest-first. Each object
        contains transaction_id, date, amount, merchant, category, and status.
    """
    try:
        cid = validate_customer_id(customer_id)
    except ValueError as exc:
        return json.dumps({"error": str(exc)})

    limit = max(1, min(limit, 50))
    txns = TRANSACTIONS.get(cid, [])
    if not txns:
        return json.dumps({"transactions": [], "message": "No transactions found."})

    # Sort by date descending
    sorted_txns = sorted(txns, key=lambda t: t["date"], reverse=True)[:limit]
    logger.info("Returned %d transactions for %s", len(sorted_txns), cid)
    return json.dumps({"customer_id": cid, "transactions": sorted_txns}, indent=2)


# ============================= TOOL 3 =====================================
@mcp.tool()
def get_transaction_detail(customer_id: str, transaction_id: str) -> str:
    """
    Get full details of a single transaction.

    Args:
        customer_id: The customer who owns the transaction (format: CUST-XXXX).
        transaction_id: The unique transaction identifier (format: TXN-XXXXX).

    Returns:
        JSON object with complete transaction details including merchant,
        amount, category, channel, and settlement status.
    """
    try:
        cid = validate_customer_id(customer_id)
        tid = validate_transaction_id(transaction_id)
    except ValueError as exc:
        return json.dumps({"error": str(exc)})

    txns = TRANSACTIONS.get(cid, [])
    match = next((t for t in txns if t["transaction_id"] == tid), None)
    if not match:
        return json.dumps(
            {"error": f"Transaction {tid} not found for customer {cid}."}
        )

    logger.info("Transaction detail: %s / %s", cid, tid)
    return json.dumps(match, indent=2)


# ============================= TOOL 4 =====================================
@mcp.tool()
def create_dispute_case(
    customer_id: str,
    transaction_id: str,
    reason: str,
    disputed_amount: float = 0.0,
) -> str:
    """
    Open a new dispute case for a specific transaction.

    Args:
        customer_id: The customer filing the dispute (format: CUST-XXXX).
        transaction_id: The transaction being disputed (format: TXN-XXXXX).
        reason: A brief description of why the transaction is disputed.
        disputed_amount: Amount being disputed (set to 0 or omit to default
                         to the full transaction amount). Must be positive
                         or zero.

    Returns:
        JSON object with the new dispute case ID, status, and summary.
    """
    try:
        cid = validate_customer_id(customer_id)
        tid = validate_transaction_id(transaction_id)
        reason = validate_reason(reason)
        # Treat 0 as "use full transaction amount"
        amt = disputed_amount if disputed_amount > 0 else None
        amt = validate_amount(amt)
    except ValueError as exc:
        return json.dumps({"error": str(exc)})

    # Verify the transaction exists
    txns = TRANSACTIONS.get(cid, [])
    txn = next((t for t in txns if t["transaction_id"] == tid), None)
    if not txn:
        return json.dumps(
            {"error": f"Transaction {tid} not found for customer {cid}."}
        )

    # Check for duplicate dispute
    for case in DISPUTE_CASES.values():
        if case["transaction_id"] == tid and case["status"] != "Closed":
            return json.dumps(
                {
                    "error": f"An open dispute already exists for {tid}.",
                    "existing_case_id": case["case_id"],
                }
            )

    # Determine disputed amount
    if amt is None:
        amt = abs(txn["amount"])

    case_id = generate_case_id()
    case = {
        "case_id": case_id,
        "customer_id": cid,
        "transaction_id": tid,
        "merchant": txn["merchant"],
        "original_amount": txn["amount"],
        "disputed_amount": amt,
        "currency": txn["currency"],
        "reason": reason,
        "status": "Open",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "resolution": None,
        "notes": "Case opened via dispute assistant. Under review.",
    }
    DISPUTE_CASES[case_id] = case

    logger.info("Dispute created: %s for txn %s (customer %s)", case_id, tid, cid)
    return json.dumps(case, indent=2)


# ============================= TOOL 5 =====================================
@mcp.tool()
def get_dispute_status(dispute_id: str) -> str:
    """
    Check the current status of a dispute case.

    Args:
        dispute_id: The dispute case identifier (format: DSP-XXXXXXXX).

    Returns:
        JSON object with the dispute case details including current status,
        resolution, and timestamps.
    """
    try:
        did = validate_dispute_id(dispute_id)
    except ValueError as exc:
        return json.dumps({"error": str(exc)})

    case = DISPUTE_CASES.get(did)
    if not case:
        return json.dumps({"error": f"Dispute case {did} not found."})

    logger.info("Dispute status lookup: %s", did)
    return json.dumps(case, indent=2)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main():
    """Run the MCP server."""
    transport = "sse" if "--sse" in sys.argv else "stdio"
    logger.info("Starting Banking MCP Server (transport=%s) ...", transport)
    mcp.run(transport=transport)


if __name__ == "__main__":
    main()

