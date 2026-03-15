"""
MCP server exposing invoice database tools.
"""
import argparse
import json
import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from db.create_database import create_database
from db.read_database import (
    get_customer_by_id as fetch_customer_by_id,
    get_invoice_details as fetch_invoice_details,
    get_invoices_for_customer as fetch_invoices_for_customer,
    get_overdue_invoices as fetch_overdue_invoices,
    list_all_invoices as fetch_all_invoices,
)

mcp = FastMCP("Invoice Database", json_response=True)
NOTIFICATIONS_LOG = Path(__file__).parent / "notifications_sent.json"

# Ensure database and tables exist on startup
create_database()


@mcp.tool()
def list_all_invoices() -> list[dict]:
    """
    Get all invoices in the database.

    Returns:
        List of invoices, each with invoice_id, customer_id, due_date, discount, tax, and total_cost.
        Ordered by invoice_id. Use this to find invoices and filter for overdue or high-value ones.
    """
    return fetch_all_invoices()


@mcp.tool()
def get_invoices_for_customer(customer_id: int) -> list[dict]:
    """
    Get all invoices for a particular customer.

    Args:
        customer_id: The customer's ID (integer).

    Returns:
        List of invoices with invoice_id, customer_id, due_date, discount, tax, and total_cost.
    """
    return fetch_invoices_for_customer(customer_id)


@mcp.tool()
def get_invoice_details(invoice_id: int) -> dict | None:
    """
    Get full details for a particular invoice, including all line items.

    Args:
        invoice_id: The invoice ID (integer).

    Returns:
        Dict with 'invoice' (invoice info) and 'items' (list of line items), or None if not found.
    """
    return fetch_invoice_details(invoice_id)


# @mcp.tool()
# def get_overdue_invoices_over_1000() -> list[dict]:
#     """
#     Find all overdue invoices with total cost greater than $1000.
#     Returns a list of invoices with invoice_id, customer_id, due_date, and total_cost.
#     Call this first to identify which customers need notifications.
#     """
#     return fetch_overdue_invoices(min_amount=1000)


@mcp.tool()
def get_customer_by_id(customer_id: int) -> dict:
    """
    Get customer details (name, email, phone, address) by customer ID.
    Use this to get contact info before sending a notification.
    """
    customer = fetch_customer_by_id(customer_id)
    return customer if customer else {"error": f"Customer {customer_id} not found"}


@mcp.tool()
def send_notification(customer_id: int, customer_name: str, customer_email: str, amount: float, invoice_ids: str) -> dict:
    """
    Send an overdue invoice notification to a customer.
    Call this for each customer who has overdue invoices over $1000.
    Args:
        customer_id: The customer's ID
        customer_name: Customer's full name
        customer_email: Customer's email address
        amount: Total overdue amount for this customer
        invoice_ids: Comma-separated list of overdue invoice IDs
    """
    notification = {
        "customer_id": customer_id,
        "customer_name": customer_name,
        "customer_email": customer_email,
        "amount": amount,
        "invoice_ids": invoice_ids,
        "message": f"Overdue payment reminder: ${amount:.2f} for invoice(s) {invoice_ids}",
    }
    existing = []
    if NOTIFICATIONS_LOG.exists():
        existing = json.loads(NOTIFICATIONS_LOG.read_text())
    existing.append(notification)
    NOTIFICATIONS_LOG.write_text(json.dumps(existing, indent=2))
    return {"status": "sent", "customer_id": customer_id, "email": customer_email}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Invoice Database MCP Server")
    parser.add_argument(
        "--http",
        action="store_true",
        help="Run with HTTP transport (default: stdio)",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host for HTTP transport")
    parser.add_argument("--port", type=int, default=8000, help="Port for HTTP transport")
    parser.add_argument("--path", default="/mcp", help="Path for HTTP transport")
    args = parser.parse_args()

    if args.http:
        # Recreate mcp with HTTP settings (host/port/path from FastMCP __init__)
        mcp.settings = type(mcp.settings)(
            **{**mcp.settings.model_dump(), "host": args.host, "port": args.port, "streamable_http_path": args.path}
        )
        print(f"MCP server started at http://{args.host}:{args.port}{args.path}", file=sys.stderr)
        mcp.run(transport="streamable-http")
    else:
        print("MCP server started successfully (stdio)", file=sys.stderr)
        mcp.run(transport="stdio")
