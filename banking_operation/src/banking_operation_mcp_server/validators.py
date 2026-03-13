"""
Input validation helpers for MCP banking tools.
Raises ValueError with user-friendly messages on bad input.
"""

import re
from typing import Optional


def validate_customer_id(customer_id: str) -> str:
    """Validate and normalise a customer ID (format: CUST-XXXX)."""
    cid = customer_id.strip().upper()
    if not re.match(r"^CUST-\d{4}$", cid):
        raise ValueError(
            f"Invalid customer_id '{customer_id}'. "
            "Expected format: CUST-XXXX (e.g. CUST-1001)."
        )
    return cid


def validate_transaction_id(transaction_id: str) -> str:
    """Validate and normalise a transaction ID (format: TXN-XXXXX)."""
    tid = transaction_id.strip().upper()
    if not re.match(r"^TXN-\d{5}$", tid):
        raise ValueError(
            f"Invalid transaction_id '{transaction_id}'. "
            "Expected format: TXN-XXXXX (e.g. TXN-50001)."
        )
    return tid


def validate_dispute_id(dispute_id: str) -> str:
    """Validate a dispute case ID (format: DSP-XXXXXXXX)."""
    did = dispute_id.strip().upper()
    if not re.match(r"^DSP-[A-Z0-9]{8}$", did):
        raise ValueError(
            f"Invalid dispute_id '{dispute_id}'. "
            "Expected format: DSP-XXXXXXXX."
        )
    return did


def validate_reason(reason: str, max_length: int = 500) -> str:
    """Validate a free-text reason field."""
    reason = reason.strip()
    if not reason:
        raise ValueError("Reason must not be empty.")
    if len(reason) > max_length:
        raise ValueError(
            f"Reason is too long ({len(reason)} chars). "
            f"Maximum allowed: {max_length}."
        )
    return reason


def validate_amount(amount: Optional[float]) -> Optional[float]:
    """Validate a disputed amount (must be positive if provided)."""
    if amount is not None and amount <= 0:
        raise ValueError("Disputed amount must be a positive number.")
    return amount

