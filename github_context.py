import os
import requests
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")

HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}

# ── HELPERS ───────────────────────────────────────────────────────────────────

def github_get(url: str) -> dict | list | None:
    """Make a GitHub API GET request. Returns None on failure."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception:
        return None

def decode_content(data: dict) -> str:
    """Decode base64 file content returned by GitHub API."""
    import base64
    try:
        content = data.get("content", "")
        return base64.b64decode(content).decode("utf-8", errors="replace")
    except Exception:
        return ""

# ── FETCHERS ──────────────────────────────────────────────────────────────────

def fetch_readme(owner: str, repo: str) -> str:
    data = github_get(f"https://api.github.com/repos/{owner}/{repo}/readme")
    if not data:
        return ""
    text = decode_content(data)
    # Truncate to first 3000 chars — enough context, not too many tokens
    return text[:3000]

def fetch_directory_tree(owner: str, repo: str) -> str:
    """Get top-2-level directory tree as a simple text list."""
    data = github_get(
        f"https://api.github.com/repos/{owner}/{repo}/git/trees/HEAD?recursive=1"
    )
    if not data:
        return ""

    tree = data.get("tree", [])
    # Filter to files only, max depth 2, skip common noise
    skip_prefixes = (".git", "node_modules", ".next", "__pycache__", ".venv", "venv", "dist", "build")
    lines = []
    seen_dirs = set()

    for item in tree:
        path = item.get("path", "")
        if any(path.startswith(s) for s in skip_prefixes):
            continue
        parts = path.split("/")
        if len(parts) <= 2:
            lines.append(path)
        elif len(parts) == 3:
            # Show the parent dir once
            parent = "/".join(parts[:2])
            if parent not in seen_dirs:
                seen_dirs.add(parent)
                lines.append(parent + "/...")

    return "\n".join(lines[:80])  # cap at 80 lines

def fetch_manifest(owner: str, repo: str) -> str:
    """Try to fetch a dependency manifest file."""
    candidates = [
        "package.json",
        "requirements.txt",
        "go.mod",
        "Cargo.toml",
        "pyproject.toml",
        "Gemfile",
        "pom.xml",
    ]
    for filename in candidates:
        data = github_get(
            f"https://api.github.com/repos/{owner}/{repo}/contents/{filename}"
        )
        if data and isinstance(data, dict):
            content = decode_content(data)
            if content:
                return f"[{filename}]\n{content[:2000]}"
    return ""

def fetch_recent_commits(owner: str, repo: str) -> str:
    """Get last 10 commit messages."""
    data = github_get(
        f"https://api.github.com/repos/{owner}/{repo}/commits?per_page=10"
    )
    if not data or not isinstance(data, list):
        return ""

    lines = []
    for commit in data:
        message = commit.get("commit", {}).get("message", "")
        first_line = message.split("\n")[0][:100]
        date = commit.get("commit", {}).get("author", {}).get("date", "")[:10]
        lines.append(f"- {first_line} ({date})")

    return "\n".join(lines)

def fetch_repo_info(owner: str, repo: str) -> dict:
    """Get basic repo metadata."""
    data = github_get(f"https://api.github.com/repos/{owner}/{repo}")
    if not data:
        return {}
    return {
        "description": data.get("description") or "",
        "language": data.get("language") or "",
        "stars": data.get("stargazers_count", 0),
        "topics": ", ".join(data.get("topics", [])),
    }

# ── MAIN CONTEXT BUILDER ──────────────────────────────────────────────────────

def build_repo_context(owner: str, repo: str) -> str:
    """
    Fetch all repo context and return as a single formatted string
    ready to be inserted into the LLM prompt.
    """
    print(f"  [github] fetching repo info...")
    info = fetch_repo_info(owner, repo)

    print(f"  [github] fetching README...")
    readme = fetch_readme(owner, repo)

    print(f"  [github] fetching directory tree...")
    tree = fetch_directory_tree(owner, repo)

    print(f"  [github] fetching manifest...")
    manifest = fetch_manifest(owner, repo)

    print(f"  [github] fetching recent commits...")
    commits = fetch_recent_commits(owner, repo)

    # Assemble context block
    parts = [f"Repository: {owner}/{repo}"]

    if info.get("description"):
        parts.append(f"Description: {info['description']}")
    if info.get("language"):
        parts.append(f"Primary language: {info['language']}")
    if info.get("topics"):
        parts.append(f"Topics: {info['topics']}")

    if readme:
        parts.append(f"\n--- README (truncated) ---\n{readme}")

    if tree:
        parts.append(f"\n--- Directory structure ---\n{tree}")

    if manifest:
        parts.append(f"\n--- Dependency manifest ---\n{manifest}")

    if commits:
        parts.append(f"\n--- Recent commits ---\n{commits}")

    return "\n".join(parts)