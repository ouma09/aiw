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
import os
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field
import requests
from starlette.responses import JSONResponse

from data import (
    CUSTOMERS,
    TRANSACTIONS,
    DISPUTE_CASES,
    generate_case_id,
)
from validators import (
    validate_customer_id,
    validate_transaction_id,
    validate_dispute_id,
    validate_reason,
    validate_amount,
)

load_dotenv()
load_dotenv("../../.env")

# configure logging
LOG_DIR = Path(__file__).resolve().parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
log_file = LOG_DIR / "mcp_server.log"
level = os.environ.get("MCP_LOG_LEVEL", "INFO").upper()
logger = logging.getLogger(__name__)
logging.basicConfig(
    format="%(asctime)s - MCP:%(levelname)s - %(filename)s:%(lineno)d - %(message)s"
)
logger.setLevel(level)

# Setup timed rotating file handler
import logging.handlers
file_handler = logging.handlers.TimedRotatingFileHandler(
    filename=str(log_file), when="D", interval=3, backupCount=1, encoding="utf-8"
)
file_handler.setFormatter(
    logging.Formatter(
        "%(asctime)s - MCP:%(levelname)s - %(filename)s:%(lineno)d - %(message)s"
    )
)
logger.addHandler(file_handler)

ENV = os.getenv("ENVIRONMENT", "production").strip().lower()
IS_DEV = ENV in {"dev", "development", "local"}

if IS_DEV:
    mcp = FastMCP(
        name="banking-dispute-server",
        host="0.0.0.0",
        port=8082,
        instructions=(
            "Banking MCP server for the Transaction Dispute Assistant. "
            "Provides tools to look up customers, view transactions, "
            "and manage dispute cases. All PII is masked."
        ),
    )
else:
    mcp = FastMCP(
        name="banking-dispute-server",
        host="0.0.0.0",
        port=8000,
        instructions=(
            "Banking MCP server for the Transaction Dispute Assistant. "
            "Provides tools to look up customers, view transactions, "
            "and manage dispute cases. All PII is masked."
        ),
    )


class CustomerProfileInput(BaseModel):
    customer_id: str = Field(
        description="The unique customer identifier (format: CUST-XXXX)."
    )

class ListTransactionsInput(BaseModel):
    customer_id: str = Field(
        description="The unique customer identifier (format: CUST-XXXX)."
    )
    limit: int = Field(
        default=10,
        description="Maximum number of transactions to return (default 10, max 50)."
    )

class TransactionDetailInput(BaseModel):
    customer_id: str = Field(
        description="The customer who owns the transaction (format: CUST-XXXX)."
    )
    transaction_id: str = Field(
        description="The unique transaction identifier (format: TXN-XXXXX)."
    )

class CreateDisputeCaseInput(BaseModel):
    customer_id: str = Field(
        description="The customer filing the dispute (format: CUST-XXXX)."
    )
    transaction_id: str = Field(
        description="The transaction being disputed (format: TXN-XXXXX)."
    )
    reason: str = Field(
        description="A brief description of why the transaction is disputed."
    )
    disputed_amount: float = Field(
        default=0.0,
        description="Amount being disputed (set to 0 or omit to default to the full transaction amount). Must be positive or zero."
    )

class DisputeStatusInput(BaseModel):
    dispute_id: str = Field(
        description="The dispute case identifier (format: DSP-XXXXXXXX)."
    )


# health_check
@mcp.custom_route("/health", methods=["GET"])
async def health_check(request) -> JSONResponse:
    return JSONResponse({"status": "ok"})


# ============================= TOOL 1 =====================================
@mcp.tool(
    name="get_customer_profile",
    description="""
    Look up a bank customer profile by their customer ID.
    Returns: JSON string with masked customer profile data including account
    status, KYC status, and risk tier. PII fields are redacted.
    """
)
def get_customer_profile(input: CustomerProfileInput) -> Dict[str, Any]:
    """
    Look up a bank customer profile by their customer ID.
    """
    logger.info("Tool 'get_customer_profile' invoked with customer_id=%s", input.customer_id)
    try:
        cid = validate_customer_id(input.customer_id)
    except ValueError as exc:
        logger.error(f"Validation error: {exc}")
        return {"error": str(exc)}

    customer = CUSTOMERS.get(cid)
    if not customer:
        logger.info("Customer lookup miss: %s", cid)
        return {"error": f"Customer {cid} not found."}

    logger.info("Customer lookup: %s", cid)
    return customer


# ============================= TOOL 2 =====================================
@mcp.tool(
    name="list_transactions",
    description="""
    Retrieve the most recent transactions for a customer.
    Returns: JSON array of transaction objects sorted newest-first. Each object
    contains transaction_id, date, amount, merchant, category, and status.
    """
)
def list_transactions(input: ListTransactionsInput) -> Dict[str, Any]:
    """
    Retrieve the most recent transactions for a customer.
    """
    logger.info("Tool 'list_transactions' invoked with customer_id=%s, limit=%s", input.customer_id, input.limit)
    try:
        cid = validate_customer_id(input.customer_id)
    except ValueError as exc:
        logger.error(f"Validation error: {exc}")
        return {"error": str(exc)}

    limit = max(1, min(input.limit, 50))
    txns = TRANSACTIONS.get(cid, [])
    if not txns:
        logger.info("No transactions found for %s", cid)
        return {"transactions": [], "message": "No transactions found."}

    # Sort by date descending
    sorted_txns = sorted(txns, key=lambda t: t["date"], reverse=True)[:limit]
    logger.info("Returned %d transactions for %s", len(sorted_txns), cid)
    return {"customer_id": cid, "transactions": sorted_txns}


# ============================= TOOL 3 =====================================
@mcp.tool(
    name="get_transaction_detail",
    description="""
    Get full details of a single transaction.
    Returns: JSON object with complete transaction details including merchant,
    amount, category, channel, and settlement status.
    """
)
def get_transaction_detail(input: TransactionDetailInput) -> Dict[str, Any]:
    """
    Get full details of a single transaction.
    """
    logger.info("Tool 'get_transaction_detail' invoked with customer_id=%s, transaction_id=%s", input.customer_id, input.transaction_id)
    try:
        cid = validate_customer_id(input.customer_id)
        tid = validate_transaction_id(input.transaction_id)
    except ValueError as exc:
        logger.error(f"Validation error: {exc}")
        return {"error": str(exc)}

    txns = TRANSACTIONS.get(cid, [])
    match = next((t for t in txns if t["transaction_id"] == tid), None)
    if not match:
        logger.info("Transaction lookup miss: %s / %s", cid, tid)
        return {"error": f"Transaction {tid} not found for customer {cid}."}

    logger.info("Transaction detail: %s / %s", cid, tid)
    return match


# ============================= TOOL 4 =====================================
@mcp.tool(
    name="create_dispute_case",
    description="""
    Open a new dispute case for a specific transaction.
    Returns: JSON object with the new dispute case ID, status, and summary.
    """
)
def create_dispute_case(input: CreateDisputeCaseInput) -> Dict[str, Any]:
    """
    Open a new dispute case for a specific transaction.
    """
    logger.info("Tool 'create_dispute_case' invoked with customer_id=%s, transaction_id=%s", input.customer_id, input.transaction_id)
    try:
        cid = validate_customer_id(input.customer_id)
        tid = validate_transaction_id(input.transaction_id)
        reason = validate_reason(input.reason)
        # Treat 0 as "use full transaction amount"
        amt = input.disputed_amount if input.disputed_amount > 0 else None
        amt = validate_amount(amt)
    except ValueError as exc:
        logger.error(f"Validation error: {exc}")
        return {"error": str(exc)}

    # Verify the transaction exists
    txns = TRANSACTIONS.get(cid, [])
    txn = next((t for t in txns if t["transaction_id"] == tid), None)
    if not txn:
        return {"error": f"Transaction {tid} not found for customer {cid}."}

    # Check for duplicate dispute
    for case in DISPUTE_CASES.values():
        if case["transaction_id"] == tid and case["status"] != "Closed":
            return {
                "error": f"An open dispute already exists for {tid}.",
                "existing_case_id": case["case_id"],
            }

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
    return case


# ============================= TOOL 5 =====================================
@mcp.tool(
    name="get_dispute_status",
    description="""
    Check the current status of a dispute case.
    Returns: JSON object with the dispute case details including current status,
    resolution, and timestamps.
    """
)
def get_dispute_status(input: DisputeStatusInput) -> Dict[str, Any]:
    """
    Check the current status of a dispute case.
    """
    logger.info("Tool 'get_dispute_status' invoked with dispute_id=%s", input.dispute_id)
    try:
        did = validate_dispute_id(input.dispute_id)
    except ValueError as exc:
        logger.error(f"Validation error: {exc}")
        return {"error": str(exc)}

    case = DISPUTE_CASES.get(did)
    if not case:
        return {"error": f"Dispute case {did} not found."}

    logger.info("Dispute status lookup: %s", did)
    return case


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main():
    """Run the MCP server."""
    import sys
    transport = "sse" if "--sse" in sys.argv else "stdio"
    logger.info("Starting Banking MCP Server (transport=%s) ...", transport)
    mcp.run(transport=transport)


if __name__ == "__main__":
    main()
