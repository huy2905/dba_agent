# Codex development instructions

Project: Vietnamese AI DBA Agent MVP, Python FastAPI.

Goals:
- Expand database adapters and read-only, version-specific skills incrementally.
- Keep all SQL in reviewed allowlisted templates; LLM may choose skill + arguments but NEVER generate executable SQL.
- Parameter-bind all user-controlled values; use low-privilege DB accounts and statement timeouts.
- Preserve credentials in environment/secret manager; do not print or commit credentials.
- Keep demo fixtures clearly labeled; never present synthetic metrics as observed real metrics.
- Write tests for SQL template selection, safety rules, metadata semantics, API, DB integration using temporary instances.
- Implement production-grade authentication, audit, rate limiting, access control before multi-user or production exposure.

Next milestones:
1) Add integration tests against a local PostgreSQL instance; validate PostgreSQL 16-18 compatibility.
2) Add SQL Server 2019 integration tests and login/database-principal distinction.
3) Improve Vietnamese intent routing and user confirmation for ambiguous targets.
4) Add Oracle adapter and tablespace/user/ASM/RAC skills.
5) Introduce metric history, authorization per target, and approval-gated write workflows.
