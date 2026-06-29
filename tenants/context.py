"""
Tenant context — per-tenant isolated storage and management.

⚠️  IMPORTANT (Vercel serverless note):
  /tmp is EPHEMERAL on Vercel — data resets on cold starts.
  For production, replace tenants/file_store.py with Vercel KV:
    1. pip install vercel-kv
    2. Replace json file reads/writes with kv.get/kv.set
    Or swap for Supabase/PlanetScale (PostgreSQL) for full persistence.
"""
import json
import os
import shutil
from pathlib import Path
from tenants import file_store

DEFAULT_PROMPT_LIMIT = 500  # Starter plan


class TenantContext:
    """
    Manages per-tenant isolated folders:
    /tmp/analystbot-data/tenant_<chat_id>/
      config.json
      history.json
      usage.json
      uploads/

    NOTE: In production (Vercel serverless), replace file_store
    with Vercel KV for persistent cross-instance storage.
    """

    def __init__(self, data_dir: str = "/tmp/analystbot-data"):
        self.data_dir = Path(data_dir)

    def _tenant_dir(self, tenant_id: str) -> Path:
        return self.data_dir / f"tenant_{tenant_id}"

    def init_tenant(self, tenant_id: str) -> dict:
        """
        Create a new tenant folder with default config.
        Idempotent — safe to call multiple times.
        Returns the tenant config dict.
        """
        td = self._tenant_dir(tenant_id)
        td.mkdir(parents=True, exist_ok=True)
        (td / "uploads").mkdir(exist_ok=True)

        config_path = td / "config.json"
        if not config_path.exists():
            config = {
                "tenant_id": tenant_id,
                "plan": "starter",
                "data_sources": [],  # list of {type, path, label}
                "created_at": self._now(),
            }
            with open(config_path, "w") as f:
                json.dump(config, f, indent=2)

        history_path = td / "history.json"
        if not history_path.exists():
            with open(history_path, "w") as f:
                json.dump([], f)

        usage_path = td / "usage.json"
        if not usage_path.exists():
            usage = {"prompts_used": 0, "limit": DEFAULT_PROMPT_LIMIT, "month": self._month()}
            with open(usage_path, "w") as f:
                json.dump(usage, f, indent=2)

        return self.get_config(tenant_id)

    def get_config(self, tenant_id: str) -> dict:
        """Load tenant config, init if missing."""
        td = self._tenant_dir(tenant_id)
        if not td.exists():
            return self.init_tenant(tenant_id)
        config_path = td / "config.json"
        if config_path.exists():
            with open(config_path) as f:
                return json.load(f)
        return self.init_tenant(tenant_id)

    def save_config(self, tenant_id: str, config: dict):
        """Save tenant config."""
        td = self._tenant_dir(tenant_id)
        td.mkdir(parents=True, exist_ok=True)
        with open(td / "config.json", "w") as f:
            json.dump(config, f, indent=2)

    def load_history(self, tenant_id: str) -> list[dict]:
        """Load conversation history."""
        td = self._tenant_dir(tenant_id)
        if not td.exists():
            return []
        history_path = td / "history.json"
        if history_path.exists():
            with open(history_path) as f:
                return json.load(f)
        return []

    def save_history(self, tenant_id: str, messages: list[dict]):
        """Save conversation history."""
        td = self._tenant_dir(tenant_id)
        td.mkdir(parents=True, exist_ok=True)
        with open(td / "history.json", "w") as f:
            json.dump(messages, f, indent=2)

    def get_usage(self, tenant_id: str) -> dict:
        """Get usage stats. Resets if new month."""
        td = self._tenant_dir(tenant_id)
        if not td.exists():
            return {"prompts_used": 0, "limit": DEFAULT_PROMPT_LIMIT, "month": self._month()}

        usage_path = td / "usage.json"
        if usage_path.exists():
            with open(usage_path) as f:
                usage = json.load(f)
            # Reset if new month
            if usage.get("month") != self._month():
                usage = {"prompts_used": 0, "limit": usage.get("limit", DEFAULT_PROMPT_LIMIT), "month": self._month()}
                with open(usage_path, "w") as f:
                    json.dump(usage, f, indent=2)
            return usage
        return {"prompts_used": 0, "limit": DEFAULT_PROMPT_LIMIT, "month": self._month()}

    def increment_usage(self, tenant_id: str):
        """Increment prompt count by 1."""
        td = self._tenant_dir(tenant_id)
        td.mkdir(parents=True, exist_ok=True)
        usage = self.get_usage(tenant_id)
        usage["prompts_used"] += 1
        with open(td / "usage.json", "w") as f:
            json.dump(usage, f, indent=2)

    def upload_file(self, tenant_id: str, filename: str, content: bytes) -> str:
        """Save an uploaded file to the tenant's uploads folder."""
        td = self._tenant_dir(tenant_id)
        td.mkdir(parents=True, exist_ok=True)
        upload_dir = td / "uploads"
        upload_dir.mkdir(exist_ok=True)
        path = upload_dir / filename
        with open(path, "wb") as f:
            f.write(content)
        return str(path)

    def get_upload_path(self, tenant_id: str, filename: str) -> str:
        return str(self._tenant_dir(tenant_id) / "uploads" / filename)

    def _now(self) -> str:
        from datetime import datetime
        return datetime.utcnow().isoformat()

    def _month(self) -> str:
        from datetime import datetime
        return datetime.utcnow().strftime("%Y-%m")

    def reset_month(self, tenant_id: str):
        """Manually reset monthly usage counter."""
        td = self._tenant_dir(tenant_id)
        usage = {"prompts_used": 0, "limit": DEFAULT_PROMPT_LIMIT, "month": self._month()}
        with open(td / "usage.json", "w") as f:
            json.dump(usage, f, indent=2)
