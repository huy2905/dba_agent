"""Natural-language -> allowlisted skill ID, never SQL."""
import json
import os
import re
import unicodedata

from .skills import SKILLS


class PlanError(ValueError):
    pass


def _ascii(text: str) -> str:
    text = unicodedata.normalize("NFD", text.lower())
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return text.replace("đ", "d")


def _fallback_plan(message: str) -> dict[str, str]:
    low = _ascii(message)
    # This is intentionally a narrow rule-based router, not a free-SQL generator.
    user_match = re.search(r"\b(?:user|login|role|tai khoan)\s+[`'\"]?([\w@.\\-]+)", low)
    username = ""
    if user_match:
        candidate = user_match.group(1).strip("`'\"")
        if candidate not in {"nao", "dang", "co", "bi", "duoc", "tren", "cua", "all", "bao", "nhieu", "list", "tất"}:
            # Recover original-case value using the same regex on original text.
            original_match = re.search(r"\b(?:user|login|role|tài khoản|tai khoan)\s+[`'\"]?([\w@.\\-]+)", message, re.I)
            username = original_match.group(1).strip("`'\"") if original_match else candidate
    if any(word in low for word in ["user", "login", "role", "tai khoan"]):
        return {"skill_id": "check_user_status" if username else "list_users", "username": username}
    if any(word in low for word in ["tablespace", "filegroup"]):
        return {"skill_id": "check_tablespace", "username": ""}
    if any(word in low for word in ["table", "bang"]):
        return {"skill_id": "check_table_size", "username": ""}
    if any(word in low for word in ["dung luong", "storage", "size", "database", "capacity"]):
        return {"skill_id": "check_database_size", "username": ""}
    raise PlanError("Chưa nhận diện được skill. Hãy hỏi về dung lượng, bảng, tablespace hoặc user.")


def _llm_plan(message: str) -> dict[str, str]:
    from openai import OpenAI

    schema = {
        "type": "object", "additionalProperties": False,
        "properties": {
            "skill_id": {"type": "string", "enum": list(SKILLS)},
            "username": {"type": "string"},
        }, "required": ["skill_id", "username"]
    }
    response = OpenAI().responses.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
        instructions=(
            "You route Vietnamese DBA requests to ONE of the listed read-only skills. "
            "Never write SQL. Never infer or fabricate a username. "
            "Use check_user_status only when the user names a specific login/role; "
            "otherwise use list_users. Only output schema-compliant JSON. "
            "This is intent classification, not execution."
        ),
        input=message,
        text={"format": {"type": "json_schema", "name": "dba_intent", "strict": True, "schema": schema}},
    )
    return json.loads(response.output_text)


def plan(message: str) -> tuple[dict[str, str], str]:
    if not message.strip():
        raise PlanError("Câu hỏi không được để trống")
    if len(message) > 1000:
        raise PlanError("Câu hỏi quá dài")
    # No mutation tools exist; reject explicit write requests early.
    if re.search(r"\b(drop|truncate|delete|update|insert|alter|grant|revoke|create|kill|shutdown|failover|restore)\b", message, re.I):
        raise PlanError("MVP chỉ hỗ trợ kiểm tra READ-ONLY; không hỗ trợ yêu cầu thay đổi DB.")
    if os.getenv("OPENAI_API_KEY"):
        try:
            request = _llm_plan(message)
            source = "llm"
        except Exception as exc:
            raise PlanError("Không thể phân tích yêu cầu bằng LLM; kiểm tra cấu hình API.") from exc
    else:
        request = _fallback_plan(message)
        source = "rules"
    if request.get("skill_id") not in SKILLS:
        raise PlanError("Skill không nằm trong allowlist")
    username = request.get("username", "")
    if not isinstance(username, str) or len(username) > 128:
        raise PlanError("Tên user không hợp lệ")
    if request["skill_id"] == "check_user_status" and not username:
        raise PlanError("Hãy cho biết tên user/login cần kiểm tra")
    return {"skill_id": request["skill_id"], "username": username}, source
