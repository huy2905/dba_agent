"""Application service. No arbitrary SQL execution endpoint is exposed."""
import logging
from time import monotonic

from .config import load_targets
from .db import execute
from .planner import plan
from .skills import SKILLS, get_query

logger = logging.getLogger("dba-agent.audit")


def chat(target_id: str, message: str) -> dict:
    inventory = load_targets()
    if target_id not in inventory:
        raise ValueError("Target không tồn tại trong cấu hình")
    target = inventory[target_id]
    request, planner = plan(message)
    skill_id = request["skill_id"]
    query = get_query(target["engine"], skill_id) if target["engine"] != "demo" else None
    start = monotonic()
    try:
        rows = execute(target, skill_id, query, username=request["username"])
    except Exception as exc:
        # Avoid leaking credentials/DSNs from driver exception messages into logs.
        logger.error("SQL execution failed target=%s skill=%s error_type=%s", target_id, skill_id, type(exc).__name__)
        raise RuntimeError("Không thể truy vấn DB. Kiểm tra network, driver và quyền read-only của target.") from None
    elapsed = round((monotonic() - start) * 1000)
    logger.info("read target=%s skill=%s rows=%s elapsed_ms=%s", target_id, skill_id, len(rows), elapsed)
    if skill_id == "check_user_status":
        info = (f"Tìm thấy user/login '{request['username']}' (theo quyền truy cập hiện có)." if rows
                else f"Không tìm thấy user/login '{request['username']}' trong phạm vi metadata được cấp quyền.")
    else:
        info = f"Trả về {len(rows)} dòng dữ liệu."
    caveat = None
    if target["engine"] == "postgresql" and skill_id in {"list_users", "check_user_status"}:
        caveat = "rolcanlogin=false không tương đương hoàn toàn ACCOUNT LOCKED của Oracle."
    if target["engine"] == "sqlserver" and skill_id in {"list_users", "check_user_status"}:
        caveat = "Kết quả kiểm tra server login; database user là đối tượng riêng. IsLocked chỉ có ý nghĩa phù hợp với SQL login."
    if skill_id in {"check_database_size", "check_tablespace"}:
        caveat = "Dung lượng file đã cấp phát không nhất thiết là dung lượng dữ liệu đang sử dụng; định nghĩa metric phụ thuộc DBMS."
    return {
        "target_id": target_id,
        "engine": target["engine"],
        "is_demo": target["engine"] == "demo",
        "skill_id": skill_id,
        "skill_description": SKILLS[skill_id],
        "planner": planner,
        "message": info,
        "caveat": caveat,
        "rows": rows,
        "row_count": len(rows),
        "duration_ms": elapsed,
        "sql_template": query.sql.strip() if query else None,
    }
