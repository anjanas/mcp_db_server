"""
Populate the database with sample data.
"""
import random
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Ensure project root is in path for db.data import when run as script
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from db.data import CITIES, FIRST_NAMES, ITEMS, LAST_NAMES, STREETS

DB_PATH = Path(__file__).resolve().parent / "invoices.db"


def populate_customers(count: int = 10, force: bool = False):
    """Populate the customers table with random customers."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if not force:
        cursor.execute("SELECT COUNT(*) FROM customers")
        if cursor.fetchone()[0] > 0:
            conn.close()
            print("Customers table already has data. Use force=True to add more.")
            return

    for _ in range(count):
        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        name = f"{first} {last}"
        address = f"{random.choice(STREETS)}, {random.choice(CITIES)}, {random.randint(10000, 99999)}"
        email = f"{first.lower()}.{last.lower()}{random.randint(1, 999)}@example.com"
        phone = f"({random.randint(200, 999)}) {random.randint(200, 999)}-{random.randint(1000, 9999)}"

        cursor.execute(
            "INSERT INTO customers (name, address, email, phone) VALUES (?, ?, ?, ?)",
            (name, address, email, phone),
        )

    conn.commit()
    conn.close()
    print(f"Inserted {count} customers into the customers table.")


def populate_invoices(force: bool = False):
    """Create invoices for half of customers. 1/3 single-item, 1/3 two-item, 1/3 three+ items."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if not force:
        cursor.execute("SELECT COUNT(*) FROM invoices")
        if cursor.fetchone()[0] > 0:
            conn.close()
            print("Invoices table already has data. Use force=True to add more.")
            return

    cursor.execute("SELECT id FROM customers ORDER BY id")
    all_customer_ids = [row[0] for row in cursor.fetchall()]
    customer_count = len(all_customer_ids)
    half_count = customer_count // 2
    customer_ids = random.sample(all_customer_ids, half_count)

    # Build invoice list: 1/3 with 1 item, 1/3 with 2 items, 1/3 with 3+ items
    invoices_to_create = []
    third = 3  # minimum invoices per tier for 9 total
    for _ in range(third):
        invoices_to_create.append(1)
    for _ in range(third):
        invoices_to_create.append(2)
    for _ in range(third):
        invoices_to_create.append(random.randint(3, 5))
    random.shuffle(invoices_to_create)

    base_date = datetime.now()
    for item_count in invoices_to_create:
        customer_id = random.choice(customer_ids)
        due_date = (base_date + timedelta(days=random.randint(7, 60))).strftime("%Y-%m-%d")
        discount = round(random.uniform(0, 0.15), 2)
        tax_rate = round(random.uniform(0.05, 0.12), 2)

        # Pick random items for this invoice
        selected_items = random.sample(ITEMS, min(item_count, len(ITEMS)))
        items_with_qty = [
            (name, description, price, random.randint(1, 3))
            for name, description, price in selected_items
        ]
        subtotal = sum(price * qty for _, _, price, qty in items_with_qty)

        discount_amount = round(subtotal * discount, 2)
        after_discount = subtotal - discount_amount
        tax_amount = round(after_discount * tax_rate, 2)
        total_cost = round(after_discount + tax_amount, 2)

        cursor.execute(
            """INSERT INTO invoices (customer_id, due_date, discount, tax, total_cost)
               VALUES (?, ?, ?, ?, ?)""",
            (customer_id, due_date, discount_amount, tax_amount, total_cost),
        )
        invoice_id = cursor.lastrowid

        for name, description, price, quantity in items_with_qty:
            cursor.execute(
                """INSERT INTO items (invoice_id, name, description, price, quantity)
                   VALUES (?, ?, ?, ?, ?)""",
                (invoice_id, name, description, price, quantity),
            )

    conn.commit()
    conn.close()
    print(f"Inserted {len(invoices_to_create)} invoices with items.")


if __name__ == "__main__":
    populate_customers(10)
    populate_invoices()
