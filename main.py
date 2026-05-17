from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from analyze import analyze_pr
from github_context import build_repo_context

app = FastAPI(title="MergeIQ API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── REQUEST / RESPONSE MODELS ─────────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    diff: str
    repo_context: str = ""
    pr_description: str = ""
    repo_owner: str = ""       # new: github owner e.g. "facebook"
    repo_name: str = ""        # new: github repo e.g. "react"

class AnalyzeResponse(BaseModel):
    summary: str
    key_changes: list
    risk_flags: list
    verdict: str
    verdict_reasoning: str
    suggested_questions: list
    confidence: str

# ── ROUTES ────────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"status": "MergeIQ API is running", "version": "0.2.0"}

@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(request: AnalyzeRequest):
    if not request.diff.strip():
        raise HTTPException(status_code=400, detail="diff cannot be empty")

    # If owner/repo provided, fetch real context from GitHub
    repo_context = request.repo_context
    if request.repo_owner and request.repo_name:
        print(f"Fetching GitHub context for {request.repo_owner}/{request.repo_name}...")
        try:
            repo_context = build_repo_context(request.repo_owner, request.repo_name)
            print(f"  Context length: {len(repo_context)} chars")
        except Exception as e:
            print(f"  Warning: GitHub context fetch failed: {e}")
            # Fall back to whatever the client sent
            repo_context = request.repo_context

    try:
        result = analyze_pr(
            repo_context=repo_context,
            diff=request.diff,
            pr_description=request.pr_description
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))