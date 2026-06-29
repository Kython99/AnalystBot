"""
Simple JSON file store for tenant data.
On Vercel serverless (stateless): uses /tmp which is per-instance ephemeral.
For production: replace with Supabase, PlanetScale, or Vercel KV.

For MVP demo purposes — data resets on each serverless cold start.
"""
import json
import os
from pathlib import Path
from typing import Optional

DATA_DIR = os.getenv("ANALYSTBOT_DATA_DIR", "/tmp/analystbot-data")

def get_path(tenant_id: str, filename: str) -> Path:
    p = Path(DATA_DIR) / f"tenant_{tenant_id}"
    p.mkdir(parents=True, exist_ok=True)
    return p / filename

def read(tenant_id: str, filename: str, default=list) -> dict | list:
    path = get_path(tenant_id, filename)
    if not path.exists():
        return default() if callable(default) else default
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return default() if callable(default) else default

def write(tenant_id: str, filename: str, data) -> None:
    path = get_path(tenant_id, filename)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def exists(tenant_id: str, filename: str) -> bool:
    return get_path(tenant_id, filename).exists()
