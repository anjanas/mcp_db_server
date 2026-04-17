# Invoice Database MCP Server

MCP server exposing invoice database tools for use with Cursor and other MCP clients.

## Setup

```bash
uv sync
```

## Database

The server uses **SQLite** (file-based). The database file is `db/invoices.db`. Create the schema first by running `uv run python db/create_database.py` (or populate sample data with `db/populate_database.py`, which expects an existing database).

**Tables:**

| Table | Purpose |
| --- | --- |
| **customers** | Customer records: `id`, `name`, `address`, `email`, `phone` |
| **invoices** | One row per invoice: `invoice_id`, `customer_id` (→ customers), `due_date`, `discount`, `tax`, `total_cost` |
| **items** | Line items per invoice: `id`, `invoice_id` (→ invoices), `name`, `description`, `price`, `quantity` |

## MCP Tools

The server registers the following tools (names are what MCP clients call):

| Tool | Parameters | What it does |
| --- | --- | --- |
| **list_all_invoices** | _(none)_ | Returns every invoice as a list of objects with `invoice_id`, `customer_id`, `due_date`, `discount`, `tax`, `total_cost`, ordered by `invoice_id`. Use for scanning or filtering (e.g. overdue amounts) in the client. |
| **get_invoices_for_customer** | `customer_id` (int) | Returns all invoices for that customer (same fields as above). |
| **get_invoice_details** | `invoice_id` (int) | Returns `{ "invoice": ..., "items": [...] }` with full line items, or `null` if the invoice does not exist. |
| **get_customer_by_id** | `customer_id` (int) | Returns customer fields (`name`, `email`, `phone`, `address`, etc.) or `{"error": "Customer … not found"}`. |
| **send_notification** | `customer_id` (int), `customer_name` (str), `customer_email` (str), `amount` (float), `invoice_ids` (str) | Records an overdue-payment style notification. Appends a JSON object to `notifications_sent.json` in the project root and returns `{"status": "sent", ...}`. `invoice_ids` is a comma-separated list of invoice IDs as a single string. |

## Run the Server

**Stdio** (default, for Cursor):
```bash
uv run python mcp_server.py
```

**HTTP** (for agent or remote clients):
```bash
uv run python mcp_server.py --http
# Listens at http://127.0.0.1:8000/mcp
# Options: --host, --port, --path
```

## Cursor Configuration

**Option A – Stdio** (spawns server when needed):

- **Transport:** stdio  
- **Command:** `uv run python mcp_server.py`  
- **Working directory:** Path to this project  

**Option B – HTTP** (server must be running first):

- **Transport:** HTTP/URL  
- **URL:** `http://127.0.0.1:8000/mcp`  
- Start server: `uv run python mcp_server.py --http`

## Overdue Invoice Agent

Agent that finds overdue invoices over $1000 and sends notifications to customers. Uses an LLM to decide which **MCP tools** to call (via `langchain-mcp-adapters`). Connects to the MCP server over **HTTP**.

**MCP tools used** (see table above): `list_all_invoices` (agent filters for overdue & amount), `get_customer_by_id`, `send_notification` (appends to `notifications_sent.json`).

**Models:** Development and testing were done with **`gpt-4o-mini`** (the default in `agent.py` for both the main agent and the judge). **Prompt 7** (overdue invoices grouped by days late—`uv run python agent.py 7`) is harder: it needs correct per-invoice date math and grouping. **`gpt-4o-mini` may fail or get inconsistent judge results** on that task; use a **stronger reasoning model** (e.g. **`o4-mini`**) for the agent and/or judge if you rely on prompt 7 in production.

**Run (2 terminals):**

Terminal 1 – start MCP server with HTTP:
```bash
uv run python mcp_server.py --http
```

Terminal 2 – run the agent:
```bash
export OPENAI_API_KEY=your-key-here
uv run python agent.py
```

Override MCP URL: `MCP_SERVER_URL=http://localhost:8000/mcp uv run python agent.py`

## Tests

**Unit tests** (default, no API key needed):
```bash
uv run pytest tests/ -v
```

**Integration test** (real LLM, requires OPENAI_API_KEY and network):
```bash
OPENAI_API_KEY=your-key uv run pytest -m integration -v
```
