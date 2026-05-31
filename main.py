from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from analyze import analyze_pr
from github_context import build_repo_context
import hmac
import hashlib
import asyncio
from fastapi import Request
import requests
from fastapi.responses import HTMLResponse


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

@app.get("/privacy", response_class=HTMLResponse)
def privacy():
    try:
        with open("privacy.html", "r") as f:
            return f.read()
    except FileNotFoundError:
        return "<h1>MergeIQ Privacy Policy</h1><p>Coming soon.</p>"

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
        
# ── WEBHOOK ───────────────────────────────────────────────────────────────────

@app.post("/webhook")
async def github_webhook(request: Request):
    from github_app import verify_webhook_signature, post_pr_comment
    from github_context import build_repo_context

    payload_bytes = await request.body()
    signature = request.headers.get("X-Hub-Signature-256", "")

    # Verify it's actually from GitHub
    if not verify_webhook_signature(payload_bytes, signature):
        print("[webhook] Invalid signature — rejecting")
        raise HTTPException(status_code=401, detail="Invalid signature")

    event = request.headers.get("X-GitHub-Event", "")

    # Parse payload once from the raw bytes
    import json as json_lib
    try:
        payload = json_lib.loads(payload_bytes)
    except Exception:
        return {"status": "invalid payload"}

    print(f"[webhook] received event: {event}")

    # Only handle pull_request events
    if event != "pull_request":
        return {"status": f"ignored event: {event}"}

    action = payload.get("action", "")
    if action not in ("opened", "synchronize", "reopened"):
        return {"status": f"ignored action: {action}"}

    # Extract PR details
    pr = payload["pull_request"]
    owner = payload["repository"]["owner"]["login"]
    repo = payload["repository"]["name"]
    pr_number = pr["number"]
    installation_id = payload["installation"]["id"]
    pr_body = pr.get("body") or ""

    print(f"[webhook] PR #{pr_number} {action} on {owner}/{repo}")

    # Run analysis in background so webhook returns fast
    asyncio.create_task(
        analyze_and_comment(owner, repo, pr_number, pr_body, installation_id)
    )

    return {"status": "processing"}


async def analyze_and_comment(
    owner: str,
    repo: str,
    pr_number: int,
    pr_body: str,
    installation_id: int
):
    from github_app import post_pr_comment, get_installation_token
    from github_context import build_repo_context

    try:
        # Fetch diff via GitHub API
        token = get_installation_token(installation_id)
        diff_response = requests.get(
            f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github.diff",
                "X-GitHub-Api-Version": "2022-11-28",
            }
        )
        diff = diff_response.text
        print(f"[webhook] diff length: {len(diff)}")

        # Fetch repo context
        print(f"[webhook] fetching context for {owner}/{repo}...")
        repo_context = build_repo_context(owner, repo)

        # Run analysis
        print(f"[webhook] running analysis...")
        analysis = analyze_pr(
            repo_context=repo_context,
            diff=diff,
            pr_description=pr_body
        )

        # Post comment
        print(f"[webhook] posting comment...")
        success = post_pr_comment(installation_id, owner, repo, pr_number, analysis)
        print(f"[webhook] comment posted: {success}")

    except Exception as e:
        import traceback
        print(f"[webhook] ERROR: {traceback.format_exc()}")