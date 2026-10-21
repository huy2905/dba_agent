"""Static skill registry. Models/users cannot inject arbitrary SQL."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Query:
    sql: str
    expects_username: bool = False


SKILLS = {
    "check_database_size": "Liệt kê dung lượng các database (file allocation tùy DBMS)",
    "check_table_size": "10 bảng chiếm nhiều dung lượng nhất của database hiện tại",
    "check_tablespace": "Dung lượng tablespace hoặc filegroup của database hiện tại",
    "list_users": "Liệt kê roles/logins trên máy chủ DB",
    "check_user_status": "Kiểm tra trạng thái một role/login bằng tên",
}

QUERIES: dict[str, dict[str, Query]] = {
    "postgresql": {
        "check_database_size": Query("""
            SELECT datname AS database_name,
                   ROUND(pg_database_size(oid)::numeric / 1048576, 2) AS allocated_mb
            FROM pg_database WHERE datallowconn
            ORDER BY pg_database_size(oid) DESC LIMIT 100
        """),
        "check_table_size": Query("""
            SELECT n.nspname AS schema_name, c.relname AS table_name,
                   ROUND(pg_total_relation_size(c.oid)::numeric / 1048576, 2) AS allocated_mb
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE c.relkind = 'r'
              AND n.nspname NOT IN ('pg_catalog', 'information_schema')
              AND n.nspname NOT LIKE 'pg_toast%'
            ORDER BY pg_total_relation_size(c.oid) DESC LIMIT 10
        """),
        "check_tablespace": Query("""
            SELECT spcname AS tablespace_name,
                   ROUND(pg_tablespace_size(oid)::numeric / 1048576, 2) AS allocated_mb
            FROM pg_tablespace
            ORDER BY pg_tablespace_size(oid) DESC LIMIT 100
        """),
        "list_users": Query("""
            SELECT rolname AS role_name, rolcanlogin AS can_login,
                   rolvaliduntil AS password_valid_until,
                   rolsuper AS is_superuser, rolcreatedb AS can_create_db
            FROM pg_roles ORDER BY rolname LIMIT 100
        """),
        "check_user_status": Query("""
            SELECT rolname AS role_name, rolcanlogin AS can_login,
                   rolvaliduntil AS password_valid_until,
                   rolsuper AS is_superuser, rolcreatedb AS can_create_db
            FROM pg_roles WHERE rolname = %s
        """, expects_username=True),
    },
    "sqlserver": {
        "check_database_size": Query("""
            SELECT TOP (100) DB_NAME(database_id) AS database_name,
                   CAST(SUM(size) * 8.0 / 1024 AS decimal(18,2)) AS allocated_mb
            FROM sys.master_files GROUP BY database_id
            ORDER BY allocated_mb DESC
        """),
        "check_table_size": Query("""
            SELECT TOP (10) s.name AS schema_name, t.name AS table_name,
                   CAST(SUM(ps.reserved_page_count) * 8.0 / 1024 AS decimal(18,2)) AS allocated_mb
            FROM sys.tables t
            JOIN sys.schemas s ON s.schema_id = t.schema_id
            JOIN sys.dm_db_partition_stats ps ON ps.object_id = t.object_id
            GROUP BY s.name, t.name
            ORDER BY allocated_mb DESC
        """),
        "check_tablespace": Query("""
            SELECT fg.name AS filegroup_name,
                   CAST(SUM(df.size) * 8.0 / 1024 AS decimal(18,2)) AS allocated_mb
            FROM sys.filegroups fg
            JOIN sys.database_files df ON df.data_space_id = fg.data_space_id
            GROUP BY fg.name ORDER BY allocated_mb DESC
        """),
        "list_users": Query("""
            SELECT TOP (100) name AS login_name, type_desc,
                   is_disabled, create_date
            FROM sys.server_principals
            WHERE type IN ('S', 'U', 'G')
            ORDER BY name
        """),
        "check_user_status": Query("""
            SELECT name AS login_name, type_desc, is_disabled,
                   CASE WHEN type = 'S' THEN LOGINPROPERTY(name, 'IsLocked') ELSE NULL END AS is_locked,
                   create_date
            FROM sys.server_principals
            WHERE name = ?
        """, expects_username=True),
    },
}


def get_query(engine: str, skill_id: str) -> Query:
    if skill_id not in SKILLS:
        raise ValueError("Unknown skill")
    try:
        return QUERIES[engine][skill_id]
    except KeyError as exc:
        raise ValueError("Skill unavailable for this engine") from exc
