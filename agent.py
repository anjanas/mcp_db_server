"""
Agent that handles invoice-related tasks.
Uses an LLM to decide which MCP tools to call.
Includes an agentic loop with LLM-as-judge: retries with feedback if the judge finds the result incorrect.

Default LLM: local Llama 3.2 via Ollama (OpenAI-compatible API). Run `ollama pull llama3.2`
and keep `ollama serve` listening (default http://127.0.0.1:11434). Override with LLM_BASE_URL,
LLM_MODEL, LLM_API_KEY in the environment or .env.

MCP server must be running with HTTP transport: uv run python mcp_server.py --http
"""
import asyncio
import os
from datetime import date
from pathlib import Path

from dotenv import load_dotenv
from openai import RateLimitError
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langchain_mcp_adapters.sessions import StreamableHttpConnection
from langchain_mcp_adapters.tools import load_mcp_tools

from prompts import FIND_FUTURE_INVOICES_COUNT, FIND_OVERDUE_INVOICES_OVER_1000, PROMPTS

load_dotenv(Path(__file__).parent / ".env")
NOTIFICATIONS_LOG = Path(__file__).parent / "notifications_sent.json"

# MCP server HTTP URL (set MCP_SERVER_URL to override)
DEFAULT_MCP_URL = "http://127.0.0.1:8000/mcp"

AGENT_TOOL_NAMES = {"list_all_invoices", "get_customer_by_id", "send_notification"}

# Local Ollama defaults (OpenAI-compatible: POST /v1/chat/completions)
_DEFAULT_LLM_BASE_URL = "http://127.0.0.1:11434/v1"
_DEFAULT_LLM_MODEL = "llama3.2"
_DEFAULT_LLM_API_KEY = "ollama"


def _default_llm() -> ChatOpenAI:
    """Chat model pointing at a local Llama 3.2 (default: Ollama)."""
    base_url = os.environ.get("LLM_BASE_URL", _DEFAULT_LLM_BASE_URL)
    model = os.environ.get("LLM_MODEL", _DEFAULT_LLM_MODEL)
    api_key = os.environ.get("LLM_API_KEY", _DEFAULT_LLM_API_KEY)
    return ChatOpenAI(model=model, base_url=base_url, api_key=api_key, temperature=0)


def _get_agent_system_prompt() -> str:
    today = date.today().isoformat()
    return f"""Today's date is {today}. An overdue invoice is one whose due_date is before today's date (due_date < today). The payment deadline has passed and the customer has not paid. Use list_all_invoices to fetch invoices, then filter for those with due_date < today and total_cost >= 1000."""

RATE_LIMIT_RETRIES = 5
RATE_LIMIT_INITIAL_DELAY = 5.0  # seconds


async def _retry_on_rate_limit(coro_factory, *, max_retries: int = RATE_LIMIT_RETRIES):
    """Execute coroutine, retrying on OpenAI rate limit with exponential backoff."""
    delay = RATE_LIMIT_INITIAL_DELAY
    last_error = None
    for attempt in range(max_retries + 1):
        try:
            return await coro_factory()
        except RateLimitError as e:
            last_error = e
            if attempt < max_retries:
                print(f"Rate limit hit, waiting {delay:.0f}s before retry ({attempt + 1}/{max_retries})...")
                await asyncio.sleep(delay)
                delay = min(delay * 2, 60)  # exponential backoff, cap at 60s
            else:
                raise
    raise last_error


def _get_judge_system() -> str:
    today = date.today().isoformat()
    return f"""You are a judge evaluating whether an AI agent completed a task correctly.

Today's date is {today}.

Definitions:
- An overdue invoice has due_date < today (payment deadline has passed).
- A future invoice has due_date >= today (not yet due).

Evaluate whether the agent completed the TASK stated in the prompt. Do not assume the task—evaluate based on what the task actually asks for (e.g. counting future invoices, finding overdue ones, sending notifications, etc.).

Respond with exactly "PASS" or "FAIL" on the first line, then a brief reason on the next line."""


def _extract_result_info(result, tools):
    """Extract tools_called, tool_results_summary, and final_response from agent result."""
    messages = result.get("messages", [])
    tool_msgs = [m for m in messages if isinstance(m, ToolMessage)]
    tool_results_str = " ".join(str(m.content) for m in tool_msgs)

    tools_called = []
    for m in messages:
        if hasattr(m, "tool_calls") and m.tool_calls:
            for tc in m.tool_calls:
                name = getattr(tc, "name", None) or (tc.get("name") if isinstance(tc, dict) else None)
                if name:
                    tools_called.append(name)

    final_response = ""
    for m in reversed(messages):
        if isinstance(m, AIMessage) and m.content:
            tool_calls = getattr(m, "tool_calls", None) or []
            if not tool_calls:
                final_response = str(m.content)
                break

    tools_available = [t.name for t in tools] if tools else []
    return tools_called, tool_results_str, final_response, tools_available


async def _llm_judge(task: str, tools_available: list[str], tools_called: list[str], tool_results_summary: str, final_response: str, llm) -> tuple[bool, str]:
    """Use an LLM as judge to evaluate whether the agent completed the task correctly. Returns (passed, reason)."""
    prompt = f"""Task: {task}

Tools available: {', '.join(tools_available)}
Tools the agent called: {', '.join(tools_called) or 'none'}

Tool results (summary): {tool_results_summary[:1500]}

Agent's final response: {final_response[:500]}

Did the agent complete the task correctly?"""

    response = await llm.ainvoke([SystemMessage(content=_get_judge_system()), HumanMessage(content=prompt)])
    content = response.content if hasattr(response, "content") else str(response)
    lines = content.strip().upper().split("\n")
    passed = lines[0].startswith("PASS") if lines else False
    return passed, content.strip()


async def run_agent(tools=None, llm=None, task: str | None = None):
    """

    Args:
        tools: Optional list of tools (for testing). If None, loads from MCP server.
        llm: Optional LLM (for testing). If None, uses local Llama 3.2 (Ollama-compatible).
        task: Optional task string. 
    """
    if tools is None:
        mcp_url = os.environ.get("MCP_SERVER_URL", DEFAULT_MCP_URL)
        connection: StreamableHttpConnection = {
            "transport": "streamable_http",
            "url": mcp_url,
        }
        tools = await load_mcp_tools(session=None, connection=connection)
        tools = [t for t in tools if t.name in AGENT_TOOL_NAMES]

    if llm is None:
        llm = _default_llm()

    agent = create_agent(llm, tools=tools, system_prompt=_get_agent_system_prompt())
    task = task

    result = await agent.ainvoke({"messages": [{"role": "user", "content": task}]})
    return result


async def run_agent_with_judge_loop(tools=None, llm=None, task: str | None = None, max_attempts: int = 3):
    """Run the agent in a loop; use LLM as judge. If judge says FAIL, retry with feedback.

    Args:
        tools: Optional list of tools (for testing). If None, loads from MCP server.
        llm: Optional LLM (for testing). If None, uses local Llama 3.2 (Ollama-compatible).
        task: Task to send to the agent. If None, uses FIND_FUTURE_INVOICES_COUNT.
        max_attempts: Maximum number of attempts before giving up.

    Returns:
        Final agent result (last attempt). Includes judge_passed and judge_reason in result metadata.
    """
    if llm is None:
        llm = _default_llm()
    judge_llm = _default_llm()

    task = task or FIND_FUTURE_INVOICES_COUNT
    base_task = task
    result = None
    tools_list = tools

    for attempt in range(1, max_attempts + 1):
        result = await _retry_on_rate_limit(lambda: run_agent(tools=tools, llm=llm, task=task))
        if tools_list is None:
            mcp_url = os.environ.get("MCP_SERVER_URL", DEFAULT_MCP_URL)
            connection: StreamableHttpConnection = {"transport": "streamable_http", "url": mcp_url}
            tools_list = await load_mcp_tools(session=None, connection=connection)
            tools_list = [t for t in tools_list if t.name in AGENT_TOOL_NAMES]

        tools_called, tool_results_str, final_response, tools_available = _extract_result_info(result, tools_list)
        passed, reason = await _retry_on_rate_limit(
            lambda: _llm_judge(
                task=task,
                tools_available=tools_available,
                tools_called=tools_called,
                tool_results_summary=tool_results_str,
                final_response=final_response,
                llm=judge_llm,
            )
        )

        if passed:
            result["judge_passed"] = True
            result["judge_reason"] = reason
            return result

        # Incorporate judge feedback for next attempt
        task = f"{base_task}\n\n[Previous attempt #{attempt} failed. Judge feedback: {reason}]"

    result["judge_passed"] = False
    result["judge_reason"] = reason
    return result


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Run the invoice agent.")
    parser.add_argument(
        "task",
        type=int,
        nargs="?",
        default=2,
        help="Task number (default: 2). Available: " + ", ".join(f"{k}" for k in PROMPTS),
    )
    args = parser.parse_args()

    if args.task not in PROMPTS:
        print(f"Unknown task {args.task}. Available: {list(PROMPTS.keys())}")
        print("Tasks:")
        for num, prompt in PROMPTS.items():
            print(f"  {num}: {prompt[:60]}...")
        return

    task = PROMPTS[args.task]
    print(f"Running agent with task {args.task}: {task[:60]}...\n")
    result = asyncio.run(run_agent_with_judge_loop(task=task))
    tools_used = []
    for msg in result.get("messages", []):
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                name = getattr(tc, "name", None) or (tc.get("name") if isinstance(tc, dict) else None)
                if name:
                    tools_used.append(name)
                    print(f"  → Used MCP tool: {name}")
        if hasattr(msg, "content") and msg.content:
            print(msg.content)
    if tools_used:
        print(f"\nMCP tools used: {', '.join(tools_used)}")
    passed = result.get("judge_passed", False)
    print(f"\nJudge: {'PASS' if passed else 'FAIL'}")
    if "judge_reason" in result:
        reason = result["judge_reason"]
        print(f"Reason: {reason[:300]}{'...' if len(reason) > 300 else ''}")
    print(f"\nNotifications logged to {NOTIFICATIONS_LOG}")


if __name__ == "__main__":
    main()
