from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from orchestrator.agent import investigate
from orchestrator.tool_registry import TOOLS

app = FastAPI(
    title="ForgeOps Lite",
    description="AI-driven incident investigation via tool orchestration",
    version="1.0.0",
)


class InvestigationRequest(BaseModel):
    query: str
    verbose: bool = False


class InvestigationResponse(BaseModel):
    rca: str
    tool_calls: list[dict]
    truncated: bool = False


@app.post("/investigate", response_model=InvestigationResponse)
def run_investigation(req: InvestigationRequest):
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="query must not be empty")
    result = investigate(req.query, verbose=req.verbose)
    return result


@app.get("/tools")
def list_tools():
    return {"tools": [{"name": t["name"], "description": t["description"]} for t in TOOLS]}


@app.get("/health")
def health():
    return {"status": "ok"}
