"""Database adapters. They execute ONLY fixed, reviewed SELECT templates."""
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from .config import dsn_for
from .skills import Query

MAX_RETURN_ROWS = 100


def _json_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, bytes):
        return "<binary redacted>"
    return value


def _fetch(cursor: Any) -> list[dict[str, Any]]:
    names = [column[0] for column in cursor.description]
    return [dict(zip(names, (_json_value(cell) for cell in row)))
            for row in cursor.fetchmany(MAX_RETURN_ROWS)]


def _postgres(target: dict, query: Query, username: str) -> list[dict[str, Any]]:
    try:
        import psycopg
    except ImportError as exc:
        raise RuntimeError("Thiếu driver PostgreSQL: pip install 'psycopg[binary]'") from exc
    with psycopg.connect(dsn_for(target), connect_timeout=5) as conn:
        with conn.cursor() as cur:
            cur.execute("BEGIN READ ONLY")
            cur.execute("SET LOCAL statement_timeout = '10000ms'")
            cur.execute(query.sql, (username,) if query.expects_username else ())
            result = _fetch(cur)
        conn.rollback()
        return result


def _sqlserver(target: dict, query: Query, username: str) -> list[dict[str, Any]]:
    try:
        import pyodbc
    except ImportError as exc:
        raise RuntimeError("Thiếu driver SQL Server: pip install pyodbc") from exc
    # SQL Server lacks a general BEGIN READ ONLY transaction. Enforce read-only
    # through a database principal with SELECT/VIEW-only permissions.
    with pyodbc.connect(dsn_for(target), timeout=5, autocommit=False) as conn:
        cursor = conn.cursor()
        cursor.timeout = 10
        try:
            cursor.execute(query.sql, (username,) if query.expects_username else ())
            result = _fetch(cursor)
            conn.rollback()
            return result
        finally:
            cursor.close()


def _demo(skill_id: str, username: str) -> list[dict[str, Any]]:
    # Clearly labeled synthetic examples; NOT actual results from any DB.
    fixtures = {
        "check_database_size": [
            {"database_name": "demo_app", "allocated_mb": 5120.00},
            {"database_name": "demo_logs", "allocated_mb": 2048.00},
        ],
        "check_table_size": [
            {"schema_name": "public", "table_name": "orders", "allocated_mb": 1024.00},
            {"schema_name": "public", "table_name": "customers", "allocated_mb": 256.00},
        ],
        "check_tablespace": [
            {"tablespace_name": "pg_default", "allocated_mb": 7168.00},
            {"tablespace_name": "pg_global", "allocated_mb": 2.00},
        ],
        "list_users": [
            {"role_name": "app_user", "can_login": True, "password_valid_until": None, "is_superuser": False},
            {"role_name": "readonly_user", "can_login": True, "password_valid_until": None, "is_superuser": False},
            {"role_name": "disabled_user", "can_login": False, "password_valid_until": None, "is_superuser": False},
        ],
    }
    if skill_id == "check_user_status":
        return [row for row in fixtures["list_users"] if row["role_name"] == username]
    return fixtures[skill_id]


def execute(target: dict, skill_id: str, query: Query | None, username: str = "") -> list[dict[str, Any]]:
    if target["engine"] == "demo":
        return _demo(skill_id, username)
    if query is None:
        raise ValueError("Missing SQL template")
    if target["engine"] == "postgresql":
        return _postgres(target, query, username)
    if target["engine"] == "sqlserver":
        return _sqlserver(target, query, username)
    raise ValueError("Unsupported engine")
