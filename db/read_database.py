"""
Read data from the invoices SQLite database.
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "invoices.db"


def get_customer_by_id(customer_id: int):
    """Return a single customer by ID, or None if not found."""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, name, address, email, phone FROM customers WHERE id = ?",
        (customer_id,),
    )
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def _get_connection():
    """Return a connection with row factory for dict-like access."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def list_all_customers():
    """Return all customers."""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, address, email, phone FROM customers ORDER BY id")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_invoices_for_customer(customer_id: int):
    """Return all invoices for a particular customer."""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT invoice_id, customer_id, due_date, discount, tax, total_cost
           FROM invoices
           WHERE customer_id = ?
           ORDER BY invoice_id""",
        (customer_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def list_all_invoices():
    """Return all invoices."""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT invoice_id, customer_id, due_date, discount, tax, total_cost
           FROM invoices
           ORDER BY invoice_id"""
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_invoice_details(invoice_id: int):
    """Return invoice details including all items for a particular invoice."""
    conn = _get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """SELECT invoice_id, customer_id, due_date, discount, tax, total_cost
           FROM invoices
           WHERE invoice_id = ?""",
        (invoice_id,),
    )
    invoice_row = cursor.fetchone()
    if invoice_row is None:
        conn.close()
        return None

    cursor.execute(
        """SELECT id, invoice_id, name, description, price, quantity
           FROM items
           WHERE invoice_id = ?
           ORDER BY id""",
        (invoice_id,),
    )
    item_rows = cursor.fetchall()
    conn.close()

    return {
        "invoice": dict(invoice_row),
        "items": [dict(row) for row in item_rows],
    }


def get_overdue_invoices(min_amount: float = 0):
    """Return all overdue invoices with total_cost >= min_amount."""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT invoice_id, customer_id, due_date, discount, tax, total_cost
           FROM invoices
           WHERE due_date < date('now') AND total_cost >= ?
           ORDER BY due_date""",
        (min_amount,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


if __name__ == "__main__":
    print("=== All Customers ===")
    for c in list_all_customers():
        print(c)

    print("\n=== All Invoices ===")
    for inv in list_all_invoices():
        print(inv)

    print("\n=== Invoices for Customer 1 ===")
    for inv in get_invoices_for_customer(1):
        print(inv)

    print("\n=== Invoice Details for Invoice 1 ===")
    details = get_invoice_details(1)
    if details:
        print("Invoice:", details["invoice"])
        print("Items:", details["items"])
