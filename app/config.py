"""Connection inventory. Credentials are resolved from environment variables."""
import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".env")


def load_targets(path: Path | None = None) -> dict[str, dict[str, Any]]:
    config_path = path or Path(os.getenv("DBA_TARGETS_FILE", str(BASE_DIR / "config/targets.json")))
    raw = json.loads(config_path.read_text(encoding="utf-8"))
    result = {}
    for entry in raw["targets"]:
        target_id = entry["id"]
        if target_id in result:
            raise ValueError(f"Duplicate target ID: {target_id}")
        if entry["engine"] not in {"demo", "postgresql", "sqlserver"}:
            raise ValueError(f"Unsupported engine for target: {target_id}")
        if entry["engine"] != "demo" and not entry.get("dsn_env"):
            raise ValueError(f"Missing dsn_env for target: {target_id}")
        result[target_id] = entry
    return result


def dsn_for(target: dict[str, Any]) -> str:
    env_name = target.get("dsn_env")
    value = os.getenv(env_name, "") if env_name else ""
    if not value:
        raise RuntimeError("Target is not configured: missing connection environment variable")
    return value
