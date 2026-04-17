"""
Unit tests for db/read_database.py using an isolated temporary SQLite database.
"""
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from db import read_database


def _create_schema(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            address TEXT,
            email TEXT,
            phone TEXT
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE invoices (
            invoice_id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            due_date TEXT NOT NULL,
            discount REAL DEFAULT 0,
            tax REAL DEFAULT 0,
            total_cost REAL NOT NULL,
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            price REAL NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 1,
            FOREIGN KEY (invoice_id) REFERENCES invoices(invoice_id)
        )
        """
    )
    conn.commit()


def _seed_test_data(conn: sqlite3.Connection) -> dict:
    """Insert known rows. Returns dict with key dates and expected ids."""
    cursor = conn.cursor()
    overdue = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")
    future = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")

    cursor.execute(
        """INSERT INTO customers (id, name, address, email, phone) VALUES
           (1, 'Alice', '1 Oak St', 'alice@example.com', '111'),
           (2, 'Bob', '2 Elm St', 'bob@example.com', '222')"""
    )

    cursor.execute(
        """INSERT INTO invoices (invoice_id, customer_id, due_date, discount, tax, total_cost) VALUES
           (1, 1, ?, 1.0, 2.0, 1500.0),
           (2, 1, ?, 0, 0, 500.0),
           (3, 1, ?, 0, 0, 2000.0),
           (4, 2, ?, 0, 0, 1200.0)""",
        (overdue, overdue, future, overdue),
    )

    cursor.execute(
        """INSERT INTO items (id, invoice_id, name, description, price, quantity) VALUES
           (1, 1, 'Widget', 'A widget', 100.0, 2),
           (2, 1, 'Gadget', NULL, 50.0, 1)"""
    )
    conn.commit()
    return {"overdue": overdue, "future": future}


@pytest.fixture
def test_db(tmp_path):
    """Temporary DB file; patches read_database.DB_PATH for the test."""
    db_path = tmp_path / "test_invoices.db"
    conn = sqlite3.connect(db_path)
    _create_schema(conn)
    meta = _seed_test_data(conn)
    conn.close()
    with patch.object(read_database, "DB_PATH", db_path):
        yield db_path, meta


def test_get_connection_returns_row_dicts(test_db):
    """_get_connection uses Row factory so columns are addressable by name."""
    _path, _meta = test_db
    conn = read_database._get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, name FROM customers WHERE id = 1")
        row = cur.fetchone()
        assert row["name"] == "Alice"
        assert row["id"] == 1
    finally:
        conn.close()


def test_get_customer_by_id_found_and_missing(test_db):
    _path, _meta = test_db
    c = read_database.get_customer_by_id(1)
    assert c == {
        "id": 1,
        "name": "Alice",
        "address": "1 Oak St",
        "email": "alice@example.com",
        "phone": "111",
    }
    assert read_database.get_customer_by_id(999) is None


def test_list_all_customers_order(test_db):
    _path, _meta = test_db
    rows = read_database.list_all_customers()
    assert [r["id"] for r in rows] == [1, 2]
    assert rows[1]["name"] == "Bob"


def test_list_all_invoices_order(test_db):
    _path, _meta = test_db
    rows = read_database.list_all_invoices()
    assert [r["invoice_id"] for r in rows] == [1, 2, 3, 4]
    inv1 = rows[0]
    assert inv1["customer_id"] == 1
    assert inv1["discount"] == 1.0
    assert inv1["tax"] == 2.0
    assert inv1["total_cost"] == 1500.0


def test_get_invoices_for_customer(test_db):
    _path, _meta = test_db
    alice = read_database.get_invoices_for_customer(1)
    assert len(alice) == 3
    assert {r["invoice_id"] for r in alice} == {1, 2, 3}

    bob = read_database.get_invoices_for_customer(2)
    assert len(bob) == 1
    assert bob[0]["invoice_id"] == 4

    assert read_database.get_invoices_for_customer(99) == []


def test_get_invoice_details_found_with_items(test_db):
    _path, _meta = test_db
    details = read_database.get_invoice_details(1)
    assert details is not None
    assert details["invoice"]["invoice_id"] == 1
    assert details["invoice"]["customer_id"] == 1
    assert len(details["items"]) == 2
    names = [i["name"] for i in details["items"]]
    assert names == ["Widget", "Gadget"]
    assert details["items"][0]["quantity"] == 2
    assert details["items"][1]["description"] is None


def test_get_invoice_details_no_items(test_db):
    _path, _meta = test_db
    details = read_database.get_invoice_details(2)
    assert details["invoice"]["invoice_id"] == 2
    assert details["items"] == []


def test_get_invoice_details_missing(test_db):
    _path, _meta = test_db
    assert read_database.get_invoice_details(999) is None


def test_get_overdue_invoices_respects_date_and_min_amount(test_db):
    _path, _meta = test_db
    overdue_only = read_database.get_overdue_invoices(min_amount=0)
    ids = {r["invoice_id"] for r in overdue_only}
    # Invoices 1,2,4 are past due; invoice 3 is future
    assert ids == {1, 2, 4}

    high = read_database.get_overdue_invoices(min_amount=1000)
    high_ids = {r["invoice_id"] for r in high}
    assert high_ids == {1, 4}
    for row in high:
        assert row["total_cost"] >= 1000
