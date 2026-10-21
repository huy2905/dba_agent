 # AI DBA Agent — MVP v0.1

An extensible Vietnamese-language DBA assistant. It accepts chat-style requests, maps them to allowlisted skills, executes fixed **read-only** queries, and displays the results.

**Current scope:** Demo mode, PostgreSQL and SQL Server adapters; five skills: database size, table size, tablespace/filegroup, list roles/logins, check role/login status. The optional OpenAI planner only classifies requests; it **cannot** execute arbitrary SQL. Without an OpenAI API key, a narrow Vietnamese rule-based router works instead.

## 1. Quick start — no DB credentials required

Python 3.10+ recommended.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000 and choose `PostgreSQL Demo (mock data)`. The dashboard clearly marks all demo results as fake. API schema: http://127.0.0.1:8000/docs.

Try:
- `Kiểm tra dung lượng các database`
- `Liệt kê 10 bảng lớn nhất`
- `Kiểm tra dung lượng tablespace`
- `Liệt kê danh sách user`
- `Kiểm tra user app_user có tồn tại không`

## 2. Connect actual database targets

1. Copy `.env.example` to `.env`; fill only the credentials for your selected DBs.
2. Copy `config/targets.example.json` to `config/targets.json`. Remove unused targets.
3. Install drivers matching your environment:

   ```bash
   pip install 'psycopg[binary]>=3.2,<4'      # PostgreSQL
   pip install 'pyodbc>=5,<6'               # SQL Server; requires unixODBC/MS ODBC Driver 18 on Linux
   ```

4. Create a **read-only account** with the specific system-catalog/DMV privileges needed by your intended skills; test per DBMS version. Configure TLS and restrictive network policy.
5. Restart FastAPI and select the actual target.

**IMPORTANT:** The `PG_PROD_DSN` example includes placeholders; do not attempt to use `CHANGE_ME`. Avoid embedding secrets in `targets.json` or Git. Prefer a secrets manager in production. `dsn_env` only names an environment variable.

## 3. (Optional) Enable AI intent planning

Set `OPENAI_API_KEY` and (optionally) `OPENAI_MODEL` in `.env`. The agent will send **only the user's request text** to the OpenAI model to classify its intent into one of the five known skills. Database rows and credentials are never sent to the model by this MVP. If no key exists, simple Vietnamese keyword rules are used instead (rule-based demo is not an LLM).

OpenAI API billing is separate from ChatGPT subscriptions. Keep confidential schema names and login details out of messages sent to third-party LLMs unless authorized by your organization. The model never supplies raw executable SQL.

## 4. API requests

```bash
curl -s http://127.0.0.1:8000/api/skills
curl -s -H 'Content-Type: application/json' -d '{"target_id":"demo-pg","message":"Kiểm tra user app_user"}' http://127.0.0.1:8000/api/chat
```

If `DBA_AGENT_API_KEY` is set, send header `X-API-Key`. This is a **basic MVP shared secret**, not production-grade user identity or authorization. Use reverse-proxy auth / SSO / RBAC, rate limiting, HTTPS, and audit before production use. Run only on `127.0.0.1` for development.

## 5. Safety and metric limitations

- The app has **no ad hoc SQL endpoint**; user/LLM input chooses only reviewed templates.
- PostgreSQL uses `BEGIN READ ONLY` and `statement_timeout`; SQL Server relies on a dedicated low-privilege DB login and command timeout (SQL Server has no equivalent general READ ONLY transaction).
- Do not connect this MVP to a production database until you have reviewed permissions, query plans, ODBC TLS settings, and server/network isolation.
- PostgreSQL `pg_roles.rolcanlogin=false` is **not** an Oracle-style account lock flag. SQL Server login status is **different** from database user membership.
- Database size/filegroup/tablespace metrics show allocation-related measurements; they do not consistently mean data actually used. MySQL/Oracle/Db2 not implemented in this v0.1.
- PostgreSQL `check_table_size` measures ordinary/leaf tables in the selected database; it does not aggregate partitioned-table parents and can return TOAST/index-inclusive numbers.
- SQL Server `sys.master_files` includes log file allocation, and the top-tables skill is scoped to the configured database.
- PostgreSQL catalog roles and SQL Server server principals have different visibility rules and require deliberate privilege review.
- This app is not a production observability platform: no persistent metric store, HA polling, backups, RBAC per target, or runbook-approval workflows yet.

## 6. Tests

```bash
pip install pytest httpx
pytest -q
```

Tests run with demo data and do not access real databases. Live integration tests are still required before deployment.

## 7. Next step using Codex

Open this folder in Codex CLI, IDE extension, or connect the Git repository to Codex Cloud. Codex can extend adapter modules, tests, user interface and the skill registry while preserving safety constraints in `AGENTS.md`.

Suggested first task:

> Read AGENTS.md and README.md. Add integration tests and expand PostgreSQL skills for replication slots, WAL retention and Patroni health, using only reviewed read-only SQL templates. Do not add any arbitrary-SQL execution capability.

## 8. Sample architecture

`Chat UI → FastAPI → (optional LLM intent router) → Skill allowlist → fixed SQL template → target DB adapter → result table`

Each target points to credentials via an environment variable. One-click extension to Oracle is not implemented: it requires an Oracle adapter, Oracle-specific SQL templates, compatible drivers, and tests.
