import os
import time
import hmac
import hashlib
import jwt
import requests
from dotenv import load_dotenv

load_dotenv()

APP_ID = os.environ.get("GITHUB_APP_ID")
WEBHOOK_SECRET = os.environ.get("GITHUB_WEBHOOK_SECRET", "")
PRIVATE_KEY_PATH = os.environ.get("GITHUB_PRIVATE_KEY_PATH", "private-key.pem")

# ── JWT GENERATION ────────────────────────────────────────────────────────────

def get_jwt_token() -> str:
    """Generate a JWT token for GitHub App authentication."""
    # Support both file path and direct env variable
    private_key = os.environ.get("GITHUB_PRIVATE_KEY", "")
    if not private_key and PRIVATE_KEY_PATH:
        with open(PRIVATE_KEY_PATH, "r") as f:
            private_key = f.read()

    # Railway env vars replace newlines with \n literally — fix that
    private_key = private_key.replace("\\n", "\n")

    now = int(time.time())
    payload = {
        "iat": now - 60,
        "exp": now + 540,
        "iss": APP_ID,
    }
    return jwt.encode(payload, private_key, algorithm="RS256")

def get_installation_token(installation_id: int) -> str:
    """Exchange JWT for an installation access token."""
    jwt_token = get_jwt_token()
    response = requests.post(
        f"https://api.github.com/app/installations/{installation_id}/access_tokens",
        headers={
            "Authorization": f"Bearer {jwt_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
    )
    return response.json()["token"]


# ── WEBHOOK VERIFICATION ──────────────────────────────────────────────────────

def verify_webhook_signature(payload_bytes: bytes, signature_header: str) -> bool:
    """Verify the webhook came from GitHub using HMAC-SHA256."""
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = hmac.new(
        WEBHOOK_SECRET.encode(),
        payload_bytes,
        hashlib.sha256
    ).hexdigest()
    received = signature_header[7:]  # strip "sha256="
    return hmac.compare_digest(expected, received)


# ── POST PR COMMENT ───────────────────────────────────────────────────────────

def post_pr_comment(
    installation_id: int,
    owner: str,
    repo: str,
    pr_number: int,
    analysis: dict
) -> bool:
    """Post MergeIQ analysis as a comment on the PR."""
    token = get_installation_token(installation_id)

    body = format_comment(analysis)

    response = requests.post(
        f"https://api.github.com/repos/{owner}/{repo}/issues/{pr_number}/comments",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        json={"body": body}
    )
    return response.status_code == 201


# ── FORMAT COMMENT ────────────────────────────────────────────────────────────

def format_comment(analysis: dict) -> str:
    """Format the analysis dict as a GitHub markdown comment."""
    verdict = analysis.get("verdict", "UNKNOWN")
    confidence = analysis.get("confidence", "")
    reasoning = analysis.get("verdict_reasoning", "")
    summary = analysis.get("summary", "")

    verdict_emoji = {
        "SAFE": "✅",
        "REVIEW_NEEDED": "⚠️",
        "RISKY": "🚨",
    }.get(verdict, "❓")

    verdict_display = verdict.replace("_", " ")

    lines = [
        "## ⚡ MergeIQ Analysis",
        "",
        f"### {verdict_emoji} {verdict_display}",
        f"*Confidence: {confidence}*",
        "",
        f"> {reasoning}",
        "",
        "### 📋 Summary",
        summary,
        "",
    ]

    # Key changes
    key_changes = analysis.get("key_changes", [])
    if key_changes:
        lines.append("### 📁 Key Changes")
        lines.append("")
        for change in key_changes:
            lines.append(f"**`{change['file']}`**")
            lines.append(f"{change['change']} — *{change['significance']}*")
            lines.append("")

    # Risk flags
    risk_flags = analysis.get("risk_flags", [])
    if risk_flags:
        lines.append("### 🚩 Risk Flags")
        lines.append("")
        severity_emoji = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}
        for flag in risk_flags:
            emoji = severity_emoji.get(flag["severity"], "⚪")
            lines.append(f"{emoji} **{flag['severity']} — {flag['type']}**")
            lines.append(f"{flag['description']}")
            lines.append("")
    else:
        lines.append("### 🚩 Risk Flags")
        lines.append("")
        lines.append("✅ No risk flags detected.")
        lines.append("")

    # Suggested questions
    questions = analysis.get("suggested_questions", [])
    if questions:
        lines.append("### ❓ Questions to Ask")
        lines.append("")
        for i, q in enumerate(questions, 1):
            lines.append(f"{i}. {q}")
        lines.append("")

    lines.append("---")
    lines.append("*Powered by [MergeIQ](https://github.com/primetree2/mergeiq) — AI-powered PR analysis*")

    return "\n".join(lines)