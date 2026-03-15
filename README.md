# Invoice Database MCP Server

MCP server exposing invoice database tools for use with Cursor and other MCP clients.

## Setup

```bash
uv sync
```

## MCP Tools

- **get_invoices_for_customer** – Get all invoices for a customer by ID
- **get_invoice_details** – Get full invoice details including line items by invoice ID

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

**MCP tools used:**
- `get_overdue_invoices_over_1000` – Find overdue invoices > $1000
- `get_customer_by_id` – Get customer contact details
- `send_notification` – Send notification (logged to `notifications_sent.json`)

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
