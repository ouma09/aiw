"""
Synthetic banking test data for the Transaction Dispute Assistant.
All data is fictional — no real PII is used.
"""

import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any

# ---------------------------------------------------------------------------
# Customers (synthetic)
# ---------------------------------------------------------------------------
CUSTOMERS: Dict[str, Dict[str, Any]] = {
    "CUST-1001": {
        "customer_id": "CUST-1001",
        "first_name": "Jane",
        "last_name": "D██",           # masked surname
        "email": "j***e@example.com",  # masked email
        "phone": "***-***-4521",       # masked phone
        "account_number": "****-****-****-7890",
        "account_type": "Checking",
        "status": "Active",
        "kyc_status": "Verified",
        "risk_tier": "Low",
        "opened_date": "2021-03-15",
    },
    "CUST-1002": {
        "customer_id": "CUST-1002",
        "first_name": "Robert",
        "last_name": "S██",
        "email": "r***t@example.com",
        "phone": "***-***-8832",
        "account_number": "****-****-****-3456",
        "account_type": "Savings",
        "status": "Active",
        "kyc_status": "Verified",
        "risk_tier": "Medium",
        "opened_date": "2019-07-22",
    },
    "CUST-1003": {
        "customer_id": "CUST-1003",
        "first_name": "Maria",
        "last_name": "G██",
        "email": "m***a@example.com",
        "phone": "***-***-1199",
        "account_number": "****-****-****-6721",
        "account_type": "Checking",
        "status": "Frozen",
        "kyc_status": "Pending Review",
        "risk_tier": "High",
        "opened_date": "2023-01-10",
    },
}

# ---------------------------------------------------------------------------
# Transactions (synthetic)
# ---------------------------------------------------------------------------
_now = datetime.utcnow()

TRANSACTIONS: Dict[str, List[Dict[str, Any]]] = {
    "CUST-1001": [
        {
            "transaction_id": "TXN-50001",
            "date": (_now - timedelta(days=1)).isoformat(),
            "amount": -124.99,
            "currency": "USD",
            "merchant": "ElectroMart Online",
            "category": "Electronics",
            "status": "Settled",
            "channel": "Online",
            "description": "Wireless headphones purchase",
        },
        {
            "transaction_id": "TXN-50002",
            "date": (_now - timedelta(days=3)).isoformat(),
            "amount": -45.00,
            "currency": "USD",
            "merchant": "GreenLeaf Grocery",
            "category": "Groceries",
            "status": "Settled",
            "channel": "POS",
            "description": "Weekly grocery shopping",
        },
        {
            "transaction_id": "TXN-50003",
            "date": (_now - timedelta(days=5)).isoformat(),
            "amount": -299.99,
            "currency": "USD",
            "merchant": "Unknown Merchant XZ9",
            "category": "Uncategorized",
            "status": "Settled",
            "channel": "Online",
            "description": "Online purchase — unrecognized",
        },
        {
            "transaction_id": "TXN-50004",
            "date": (_now - timedelta(days=7)).isoformat(),
            "amount": 2500.00,
            "currency": "USD",
            "merchant": "Employer Direct Deposit",
            "category": "Income",
            "status": "Settled",
            "channel": "ACH",
            "description": "Payroll deposit",
        },
        {
            "transaction_id": "TXN-50005",
            "date": (_now - timedelta(days=10)).isoformat(),
            "amount": -89.50,
            "currency": "USD",
            "merchant": "CloudFit Gym",
            "category": "Health & Fitness",
            "status": "Settled",
            "channel": "Recurring",
            "description": "Monthly gym membership",
        },
    ],
    "CUST-1002": [
        {
            "transaction_id": "TXN-60001",
            "date": (_now - timedelta(days=2)).isoformat(),
            "amount": -1200.00,
            "currency": "USD",
            "merchant": "LuxStay Hotels",
            "category": "Travel",
            "status": "Settled",
            "channel": "Online",
            "description": "Hotel reservation — 2 nights",
        },
        {
            "transaction_id": "TXN-60002",
            "date": (_now - timedelta(days=4)).isoformat(),
            "amount": -67.30,
            "currency": "USD",
            "merchant": "FuelUp Station #42",
            "category": "Auto & Transport",
            "status": "Settled",
            "channel": "POS",
            "description": "Fuel purchase",
        },
        {
            "transaction_id": "TXN-60003",
            "date": (_now - timedelta(days=6)).isoformat(),
            "amount": -499.99,
            "currency": "USD",
            "merchant": "Unknown Merchant QR7",
            "category": "Uncategorized",
            "status": "Settled",
            "channel": "Online",
            "description": "Subscription charge — not recognized",
        },
    ],
    "CUST-1003": [
        {
            "transaction_id": "TXN-70001",
            "date": (_now - timedelta(days=1)).isoformat(),
            "amount": -55.00,
            "currency": "USD",
            "merchant": "QuickBite Delivery",
            "category": "Food & Dining",
            "status": "Pending",
            "channel": "Online",
            "description": "Food delivery order",
        },
    ],
}

# ---------------------------------------------------------------------------
# Dispute cases (mutable — created at runtime)
# ---------------------------------------------------------------------------
DISPUTE_CASES: Dict[str, Dict[str, Any]] = {}


def generate_case_id() -> str:
    """Return a unique dispute case ID."""
    return f"DSP-{uuid.uuid4().hex[:8].upper()}"

