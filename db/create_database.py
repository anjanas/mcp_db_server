"""
Create SQLite database with invoices, items, and customers tables.
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "invoices.db"


def create_database():
    """Create the SQLite database and all tables."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Customers table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            address TEXT,
            email TEXT,
            phone TEXT
        )
    """)

    # 2. Invoices table (references customers)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS invoices (
            invoice_id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            due_date TEXT NOT NULL,
            discount REAL DEFAULT 0,
            tax REAL DEFAULT 0,
            total_cost REAL NOT NULL,
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        )
    """)

    # 3. Items table (references invoices - one invoice can have many items)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            price REAL NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 1,
            FOREIGN KEY (invoice_id) REFERENCES invoices(invoice_id)
        )
    """)

    conn.commit()
    conn.close()
    print(f"Database created successfully at {DB_PATH}")


if __name__ == "__main__":
    create_database()
