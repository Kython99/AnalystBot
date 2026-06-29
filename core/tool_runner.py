"""
Tool runner — executes tools safely and returns results to the agent.
Each tool is a function that takes (tenant_id: str, **kwargs) -> str.
"""
import json
import importlib
import pkgutil
from typing import Any


class ToolRunner:
    """
    Loads and executes tools for a given tenant.
    Tools live in the `tools/` package and must follow the signature:
        def run(tenant_id: str, **kwargs) -> str
    """

    def __init__(self, tools_dir: str = "tools"):
        self.tools_dir = tools_dir
        self._tools: dict[str, callable] = {}
        self._discover_tools()

    def _discover_tools(self):
        """Auto-discover all tools in the tools package."""
        try:
            from tools import excel, sheets, report
            for mod in [excel, sheets, report]:
                for name in dir(mod):
                    obj = getattr(mod, name)
                    if callable(obj) and not name.startswith("_"):
                        self._tools[name] = obj
        except Exception as e:
            print(f"Warning: could not discover tools: {e}")

    def list_tools(self) -> list[str]:
        """Return all available tool names."""
        return list(self._tools.keys())

    def run(self, tool_name: str, tenant_id: str, **kwargs: Any) -> str:
        """
        Execute a tool by name for a given tenant.

        Args:
            tool_name: Name of the tool function
            tenant_id: Tenant identifier
            **kwargs: Arguments to pass to the tool

        Returns:
            Tool output as string, or error message
        """
        if tool_name not in self._tools:
            return f"Error: unknown tool '{tool_name}'. Available tools: {self.list_tools()}"

        try:
            result = self._tools[tool_name](tenant_id=tenant_id, **kwargs)
            return str(result)
        except Exception as e:
            return f"Error running tool '{tool_name}': {e}"

    def run_multiple(self, tool_calls: list[dict], tenant_id: str) -> list[dict]:
        """
        Execute multiple tool calls and return results.
        Each tool_call: {"name": str, "args": dict}

        Returns:
            [{"name": str, "result": str}, ...]
        """
        results = []
        for call in tool_calls:
            name = call.get("name", "")
            args = call.get("args", {})
            result = self.run(name, tenant_id, **args)
            results.append({"name": name, "result": result})
        return results
