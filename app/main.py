"""FastAPI app, localhost-only by default when launched as documented."""
import os
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from .config import load_targets
from .planner import PlanError
from .service import chat
from .skills import SKILLS

app = FastAPI(title="AI DBA Agent MVP", version="0.1.0", docs_url="/docs")
STATIC = Path(__file__).parent / "static" / "index.html"


def check_api_key(x_api_key: str | None = Header(default=None)) -> None:
    configured = os.getenv("DBA_AGENT_API_KEY", "")
    if configured and x_api_key != configured:
        raise HTTPException(status_code=401, detail="Invalid API key")


class ChatRequest(BaseModel):
    target_id: str = Field(min_length=1, max_length=100)
    message: str = Field(min_length=1, max_length=1000)


@app.get("/")
def index():
    return FileResponse(STATIC)


@app.get("/api/health")
def health():
    return {"ok": True, "service": "AI DBA Agent MVP"}


@app.get("/api/targets", dependencies=[Depends(check_api_key)])
def targets():
    return [{"id": item["id"], "label": item["label"], "engine": item["engine"]}
            for item in load_targets().values()]


@app.get("/api/skills", dependencies=[Depends(check_api_key)])
def skills():
    return [{"id": skill, "description": desc} for skill, desc in SKILLS.items()]


@app.post("/api/chat", dependencies=[Depends(check_api_key)])
def execute_chat(request: ChatRequest):
    try:
        return chat(request.target_id, request.message)
    except (ValueError, PlanError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
