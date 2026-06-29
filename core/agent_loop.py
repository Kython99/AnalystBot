"""
The agent loop — the core brain of AnalystBot.
Handles: receive message → load tenant context → LLM → tool calls → save history → return.
"""
import json
import os
import re
from typing import Optional

from core.llm import completion
from core.tool_runner import ToolRunner
from tenants.context import TenantContext

SYSTEM_PROMPT = """You are AnalystBot — a sharp, business-focused data analyst AI agent.

Your job:
- Read and analyse the tenant's sales data (CSV, Excel, Google Sheets)
- Summarise sales performance: totals, trends, top products, problem areas
- Give actionable, specific recommendations
- Answer follow-up questions clearly and concisely
- Never make up numbers. If you don't have data, say so.

Rules:
- Be direct and practical — business users need insights, not caveats
- Format numbers clearly (e.g. "$12,500" not "12499.50")
- Flag anomalies clearly (e.g. "⚠️ Sales dropped 30% in March")
- When you need to read data, call the appropriate tool (read_csv, read_sheets, etc.)
- When you have all the data you need, give a clear summary or answer

You have access to these tools:
- read_csv: Read a CSV file from the tenant's uploads folder
- read_excel: Read an Excel (.xlsx) file from the tenant's uploads folder
- read_sheets: Read data from a Google Sheets shareable link
- generate_report: Generate a structured sales summary and recommendations

Always cite specific data points in your responses (e.g. "March revenue was $X, down Y% from February")."""

TOOL_CALL_RE = re.compile(r'<tool_call>(.*?)</tool_call>', re.DOTALL)
TOOL_ARG_RE = re.compile(r'<tool_name>(.*?)</tool_name>\s*<args>(.*?)</args>', re.DOTALL)


class AgentLoop:
    """
    Multi-tenant agent loop.
    Each tenant gets isolated context (history, config, usage).
    """

    def __init__(self, data_dir: str = "/root/analystbot-data"):
        self.data_dir = data_dir
        self.tenant_ctx = TenantContext(data_dir)
        self.tool_runner = ToolRunner()

    def parse_tool_calls(self, text: str) -> list[dict]:
        """Extract tool calls from LLM response text."""
        calls = []
        for block in TOOL_CALL_RE.findall(text):
            name_match = TOOL_ARG_RE.search(block)
            if name_match:
                name = name_match.group(1).strip()
                args_raw = name_match.group(2).strip()
                try:
                    args = json.loads(args_raw)
                except json.JSONDecodeError:
                    args = {}
                calls.append({"name": name, "args": args})
        return calls

    def run(self, tenant_id: str, user_message: str) -> str:
        """
        Run the full agent loop for a tenant.

        Args:
            tenant_id: Telegram chat_id (used as tenant identifier)
            user_message: The user's message

        Returns:
            The agent's response string
        """
        # 1. Check + enforce usage cap
        usage = self.tenant_ctx.get_usage(tenant_id)
        limit = usage.get("limit", 500)
        used = usage.get("prompts_used", 0)
        if used >= limit:
            return (
                "⚠️ You've reached your monthly prompt limit. "
                "Upgrade your plan or wait until next month."
            )

        # 2. Load conversation history
        history = self.tenant_ctx.load_history(tenant_id)

        # 3. Build messages list for LLM
        messages = history + [{"role": "user", "content": user_message}]

        # 4. Call LLM
        response_text = completion(SYSTEM_PROMPT, messages)
        messages.append({"role": "assistant", "content": response_text})

        # 5. Parse and execute tool calls (loop until no more tools)
        max_loops = 5
        loop_count = 0
        while loop_count < max_loops:
            tool_calls = self.parse_tool_calls(response_text)
            if not tool_calls:
                break

            loop_count += 1
            tool_results = self.tool_runner.run_multiple(tool_calls, tenant_id)

            # Append tool results as user messages to continue the conversation
            for tr in tool_results:
                tool_msg = f"[Tool: {tr['name']}]\n{tr['result']}"
                messages.append({"role": "user", "content": tool_msg})

            # Re-call LLM with tool results
            response_text = completion(SYSTEM_PROMPT, messages)
            messages.append({"role": "assistant", "content": response_text})

        # 6. Save history
        self.tenant_ctx.save_history(tenant_id, messages[1:])  # skip the initial user msg

        # 7. Increment usage
        self.tenant_ctx.increment_usage(tenant_id)

        return response_text

    def process(self, tenant_id: str, user_message: str) -> str:
        """
        Alias for run(). Public entry point.
        """
        return self.run(tenant_id, user_message)
