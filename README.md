# ⚡ MergeIQ

**AI-powered pull request analysis — understand what changed, why it matters, and whether it's safe to merge.**

MergeIQ is a Chrome extension + deployed API that sits alongside GitHub's PR interface. It reads the diff, fetches real repo context, and uses Gemini AI to give you a structured, plain-English analysis of every pull request — in seconds.

---

## What it does

When you open a pull request on GitHub and click **Analyze this PR**, MergeIQ:

- Scrapes the diff directly from the GitHub UI
- Fetches the repo's README, directory tree, dependency manifests, and recent commits via the GitHub API
- Sends everything to Gemini with a structured prompt
- Returns a full analysis in a sidebar panel:

| Section | What you get |
|---|---|
| **Verdict** | `SAFE`, `REVIEW NEEDED`, or `RISKY` with confidence level |
| **Summary** | Plain-English explanation of what the PR actually does |
| **Key Changes** | File-by-file breakdown of significant modifications |
| **Risk Flags** | Specific issues flagged with `LOW`, `MEDIUM`, or `HIGH` severity |
| **Questions to ask** | Suggested questions for the PR author before merging |

---

## Demo

> Open a GitHub PR → click **Files changed** → click **Analyze this PR**

The sidebar appears on the right side of any GitHub pull request page automatically.

---

## Tech stack

| Layer | Technology |
|---|---|
| Chrome extension | Manifest V3, vanilla JS |
| Backend API | Python, FastAPI, Uvicorn |
| AI model | Google Gemini 2.5 Flash |
| Repo context | GitHub REST API |
| Deployment | Railway |

---

## Project structure

```
mergeiq/
├── analyze.py          # Core LLM prompt logic
├── main.py             # FastAPI server with /analyze endpoint
├── github_context.py   # GitHub API fetcher (README, tree, manifests, commits)
├── requirements.txt    # Python dependencies
├── Procfile            # Railway deployment config
└── extension/
    ├── manifest.json   # Chrome extension config
    ├── content.js      # Diff scraper + sidebar injector
    ├── sidebar.css     # Sidebar styles
    ├── icon16.png
    ├── icon48.png
    └── icon128.png
```

---

## Running locally

### 1. Clone the repo

```bash
git clone https://github.com/primetree2/mergeiq.git
cd mergeiq
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Set up environment variables

Create a `.env` file in the root directory:

```
GEMINI_API_KEY=your-google-ai-studio-key
GITHUB_TOKEN=your-github-personal-access-token
```

- Get a Gemini API key at [aistudio.google.com](https://aistudio.google.com)
- Create a GitHub token at [github.com/settings/tokens](https://github.com/settings/tokens) with `repo` scope

### 4. Start the server

```bash
python -m uvicorn main:app --reload
```

Server runs at `http://127.0.0.1:8000`. Visit `/docs` for the interactive API explorer.

### 5. Load the Chrome extension

1. Open `chrome://extensions` in Chrome or Brave
2. Enable **Developer mode**
3. Click **Load unpacked**
4. Select the `extension/` folder

---

## API

### `POST /analyze`

Analyzes a pull request diff with optional repo context.

**Request body:**

```json
{
  "diff": "string (required) — the raw unified diff",
  "repo_context": "string (optional) — fallback context if owner/repo not provided",
  "pr_description": "string (optional) — PR body text from the author",
  "repo_owner": "string (optional) — GitHub repo owner",
  "repo_name": "string (optional) — GitHub repo name"
}
```

**Response:**

```json
{
  "summary": "string",
  "key_changes": [{ "file": "string", "change": "string", "significance": "string" }],
  "risk_flags": [{ "type": "string", "severity": "LOW|MEDIUM|HIGH", "description": "string" }],
  "verdict": "SAFE|REVIEW_NEEDED|RISKY",
  "verdict_reasoning": "string",
  "suggested_questions": ["string"],
  "confidence": "HIGH|MEDIUM|LOW"
}
```

---

## Deployment

The backend is deployed on [Railway](https://railway.app). To deploy your own instance:

1. Fork this repo
2. Create a new Railway project → Deploy from GitHub
3. Add environment variables: `GEMINI_API_KEY` and `GITHUB_TOKEN`
4. Railway auto-deploys on every push to `main`
5. Update `API_URL` in `extension/content.js` with your Railway domain
6. Update `host_permissions` in `extension/manifest.json` with your Railway domain
7. Reload the extension

---

## Roadmap

- [ ] Loading spinner with progress feedback
- [ ] Analysis caching (skip re-analyzing unchanged PRs)
- [ ] GitHub App — auto-post analysis as PR comment
- [ ] Web dashboard — history of analyzed PRs
- [ ] Per-repo risk rule configuration
- [ ] GitLab support
- [ ] Chrome Web Store listing

---

## License

MIT
