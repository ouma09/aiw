"""
Standalone smoke test - verifies the MCP server starts and all tools
return valid JSON without requiring an LLM API key.

Usage:
    python test_server.py
"""

import asyncio
import json
import os
import sys

# Force UTF-8 output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def smoke_test():
    server_params = StdioServerParameters(
        command="python",
        args=["-m", "mcp_server.server"],
        env={**os.environ},
    )

    print("=" * 60)
    print("  Banking MCP Server - Smoke Test")
    print("=" * 60)

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # 1. List tools
            tools = await session.list_tools()
            tool_names = [t.name for t in tools.tools]
            print(f"\n[OK] Tools discovered: {tool_names}")
            assert len(tool_names) >= 2, "Expected at least 2 tools"

            # 2. get_customer_profile - valid
            print("\n--- get_customer_profile(CUST-1001) ---")
            r = await session.call_tool(
                "get_customer_profile", {"customer_id": "CUST-1001"}
            )
            data = json.loads(r.content[0].text)
            print(json.dumps(data, indent=2))
            assert "customer_id" in data

            # 3. get_customer_profile - invalid ID
            print("\n--- get_customer_profile(BAD-ID) ---")
            r = await session.call_tool(
                "get_customer_profile", {"customer_id": "BAD-ID"}
            )
            data = json.loads(r.content[0].text)
            print(json.dumps(data, indent=2))
            assert "error" in data

            # 4. list_transactions
            print("\n--- list_transactions(CUST-1001, limit=3) ---")
            r = await session.call_tool(
                "list_transactions",
                {"customer_id": "CUST-1001", "limit": 3},
            )
            data = json.loads(r.content[0].text)
            print(json.dumps(data, indent=2))
            assert "transactions" in data

            # 5. get_transaction_detail
            print("\n--- get_transaction_detail(CUST-1001, TXN-50003) ---")
            r = await session.call_tool(
                "get_transaction_detail",
                {"customer_id": "CUST-1001", "transaction_id": "TXN-50003"},
            )
            data = json.loads(r.content[0].text)
            print(json.dumps(data, indent=2))
            assert data["transaction_id"] == "TXN-50003"

            # 6. create_dispute_case
            print("\n--- create_dispute_case(CUST-1001, TXN-50003, ...) ---")
            r = await session.call_tool(
                "create_dispute_case",
                {
                    "customer_id": "CUST-1001",
                    "transaction_id": "TXN-50003",
                    "reason": "I did not make this purchase. The merchant is unknown to me.",
                },
            )
            data = json.loads(r.content[0].text)
            print(json.dumps(data, indent=2))
            assert "case_id" in data
            case_id = data["case_id"]

            # 7. get_dispute_status
            print(f"\n--- get_dispute_status({case_id}) ---")
            r = await session.call_tool(
                "get_dispute_status", {"dispute_id": case_id}
            )
            data = json.loads(r.content[0].text)
            print(json.dumps(data, indent=2))
            assert data["status"] == "Open"

            # 8. Duplicate dispute - should error
            print("\n--- create_dispute_case (duplicate) ---")
            r = await session.call_tool(
                "create_dispute_case",
                {
                    "customer_id": "CUST-1001",
                    "transaction_id": "TXN-50003",
                    "reason": "Duplicate attempt",
                },
            )
            data = json.loads(r.content[0].text)
            print(json.dumps(data, indent=2))
            assert "error" in data

    print("\n" + "=" * 60)
    print("  [PASS] All smoke tests PASSED")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(smoke_test())
