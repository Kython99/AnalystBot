"""
Tenant registry — maps Telegram chat_id to internal tenant_id.
chat_id IS the tenant_id (simpler, no mapping needed).
"""
from tenants.context import TenantContext


class TenantRegistry:
    """
    Maps external identifiers (Telegram chat_id) to internal tenant records.
    For now, chat_id == tenant_id (they are the same number).
    """

    def __init__(self, data_dir: str = "/root/analystbot-data"):
        self.ctx = TenantContext(data_dir)

    def get_or_create(self, chat_id: str) -> dict:
        """
        Get a tenant by chat_id, creating their folder if it doesn't exist.
        Returns the tenant config dict.
        """
        return self.ctx.init_tenant(chat_id)

    def get_plan(self, chat_id: str) -> str:
        """Return the tenant's plan tier."""
        config = self.ctx.get_config(chat_id)
        return config.get("plan", "starter")

    def set_plan(self, chat_id: str, plan: str):
        """Update a tenant's plan tier."""
        config = self.ctx.get_config(chat_id)
        config["plan"] = plan
        # Update usage limit based on plan
        limits = {"starter": 500, "growth": 2000, "pro": 999999}
        usage = self.ctx.get_usage(chat_id)
        usage["limit"] = limits.get(plan, 500)
        self.ctx.save_config(chat_id, config)
