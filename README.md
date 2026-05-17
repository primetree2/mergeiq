<div align="center">

<br/>

# ⚡ MergeIQ

### *A Chrome extension + GitHub Bot that automatically reviews every pull request using AI — so you always know what changed, what's risky, and whether it's safe to merge.*

<br/>

[![Live API](https://img.shields.io/badge/API-Live%20on%20Railway-7ee787?style=for-the-badge&logo=railway&logoColor=white)](https://web-production-6f4dd.up.railway.app)
[![Chrome Extension](https://img.shields.io/badge/Extension-Chrome%20%2F%20Brave-4285F4?style=for-the-badge&logo=googlechrome&logoColor=white)](#-getting-started)
[![GitHub App](https://img.shields.io/badge/GitHub%20App-Auto%20Comments-238636?style=for-the-badge&logo=github&logoColor=white)](#-github-app)
[![Powered by Gemini](https://img.shields.io/badge/AI-Gemini%202.5%20Flash-886FBF?style=for-the-badge&logo=google&logoColor=white)](https://aistudio.google.com)

<br/>

> *You open a pull request. Before you even read the first line of diff,*
> *MergeIQ has already told you what changed, what risks exist, and whether it's safe to merge.*

<br/>

</div>

---

## 👋 What is MergeIQ?

MergeIQ is an AI-powered pull request analysis tool that sits alongside GitHub's PR interface. Instead of spending 30 minutes reading through a wall of red and green lines, you get a structured, plain-English summary of every pull request — in seconds.

It works in **two ways**:

| Mode | How it works |
|---|---|
| 🔌 **Chrome Extension** | Click "Analyze this PR" in the MergeIQ sidebar on any GitHub PR page |
| 🤖 **GitHub App** | Installs on your repo — automatically posts an analysis comment the moment any PR is opened |

Both modes fetch real context about your repository (README, folder structure, dependencies, recent commits) and send it to Gemini AI alongside the diff — so the analysis understands your project, not just the changed lines.

---

## ✨ What You Get

Every PR analysis produces a structured report:

```
⚡ MergeIQ Analysis

✅ SAFE  (Confidence: HIGH)
   The change is limited to documentation — no functional impact.

📋 Summary
   This PR updates the README to reflect the new deployment process
   and adds setup instructions for Windows users.

📁 Key Changes
   README.md — Added Windows setup section and updated Railway deploy steps.

🚩 Risk Flags
   ✅ No risk flags detected.

❓ Questions to ask
   No questions needed — this PR is self-explanatory.

Powered by MergeIQ — AI-powered PR analysis
```

**Verdict options:** `✅ SAFE` · `⚠️ REVIEW NEEDED` · `🚨 RISKY`

**Risk severities:** `🟢 LOW` · `🟡 MEDIUM` · `🔴 HIGH`

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     CLIENT LAYER                        │
│                                                         │
│   Chrome Extension          GitHub App (Webhook)        │
│   • Scrapes PR diff         • Receives PR events        │
│   • Sidebar UI panel        • No extension needed       │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTPS
                       ▼
┌─────────────────────────────────────────────────────────┐
│                  BACKEND · FastAPI                      │
│                                                         │
│   /analyze endpoint         /webhook endpoint           │
│   • Diff parser             • Signature verification    │
│   • GitHub context builder  • Background task runner    │
│   • Prompt assembler        • PR comment poster         │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│                  LLM · Gemini 2.5 Flash                 │
│                                                         │
│   temperature: 0.1 for consistent, reliable outputs     │
│   Structured JSON response with verdict + confidence    │
└─────────────────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
mergeiq/
│
├── analyze.py              # Core Gemini prompt logic + JSON parsing
├── main.py                 # FastAPI server (/analyze + /webhook routes)
├── github_context.py       # GitHub API: README, tree, manifests, commits
├── github_app.py           # JWT auth, webhook verification, PR comments
│
├── requirements.txt        # Python dependencies
├── Procfile                # Railway deployment config
│
└── extension/
    ├── manifest.json       # Chrome MV3 config
    ├── content.js          # Diff scraper + sidebar injector
    ├── sidebar.css         # Sidebar styles
    ├── icon16.png
    ├── icon48.png
    └── icon128.png
```

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- A [Google AI Studio](https://aistudio.google.com) API key (Gemini)
- A GitHub Personal Access Token with `repo` scope
- Chrome or Brave browser

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

```env
GEMINI_API_KEY=your_gemini_api_key_here
GITHUB_TOKEN=your_github_personal_access_token_here

# Only needed for the GitHub App feature:
GITHUB_APP_ID=your_app_id
GITHUB_WEBHOOK_SECRET=your_webhook_secret
GITHUB_PRIVATE_KEY=your_pem_file_contents
```

> ⚠️ **Never commit `.env` to git.** It's already in `.gitignore`.

### 4. Start the server

```bash
python -m uvicorn main:app --reload
```

Server runs at `http://127.0.0.1:8000` — visit `/docs` for the interactive API explorer.

### 5. Load the Chrome extension

1. Open `chrome://extensions` (or `brave://extensions`)
2. Enable **Developer mode** (top right toggle)
3. Click **Load unpacked**
4. Select the `extension/` folder

The MergeIQ icon will appear in your browser toolbar. ⚡

---

## 🔌 Using the Extension

1. Navigate to any GitHub pull request
2. Click the **Files changed** tab so the diff is visible
3. The MergeIQ sidebar appears on the right
4. Click **Analyze this PR**
5. Watch the 4-step loader as MergeIQ reads the diff, fetches repo context, runs AI analysis, and renders results

---

## 🤖 GitHub App

The GitHub App mode requires no browser extension. Once installed on a repo, MergeIQ automatically posts a full analysis comment on every new pull request — visible to the whole team, before the repo owner has even opened it.

```
How the GitHub Bot works:

  Someone opens a PR
          │
          ▼
  GitHub sends a webhook to MergeIQ's server
          │
          ▼
  MergeIQ fetches the full diff via GitHub API
          │
          ▼
  MergeIQ fetches repo context
  (README · folder structure · dependencies · recent commits)
          │
          ▼
  Everything is sent to Gemini AI with a structured prompt
          │
          ▼
  Gemini returns: verdict · summary · risk flags · questions
          │
          ▼
  MergeIQ posts the analysis as a comment on the PR
  (visible to the whole team — before anyone has read a single line)
```

### Setup

1. Go to **github.com → Settings → Developer settings → GitHub Apps → New GitHub App**
2. Set the Webhook URL to: `https://your-railway-url.up.railway.app/webhook`
3. Set Repository permissions: **Pull requests → Read & Write**, **Contents → Read only**
4. Subscribe to **Pull request** events
5. Generate a private key — save the `.pem` file
6. Add `GITHUB_APP_ID`, `GITHUB_WEBHOOK_SECRET`, and `GITHUB_PRIVATE_KEY` to Railway environment variables
7. Install the app on any repo from the **Install App** tab

From that point — every PR gets an automatic MergeIQ analysis comment. No clicks, no extensions, no setup for contributors.

---

## 🌐 API Reference

### `POST /analyze`

**Request:**

```json
{
  "diff": "string (required)",
  "repo_context": "string (optional)",
  "pr_description": "string (optional)",
  "repo_owner": "string (optional)",
  "repo_name": "string (optional)"
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

### `POST /webhook`

GitHub App webhook endpoint. Verifies HMAC-SHA256 signature and processes `pull_request` events asynchronously.

---

## ☁️ Deployment

MergeIQ's backend is deployed on [Railway](https://railway.app).

1. Fork this repo
2. Create a new Railway project → **Deploy from GitHub repo**
3. Add environment variables in the **Variables** tab
4. Railway auto-deploys on every push to `main`
5. Generate a domain in **Settings → Networking**
6. Update `API_URL` in `extension/content.js` with your Railway domain
7. Update `host_permissions` in `extension/manifest.json` with your Railway domain
8. Reload the extension

---

## 🗺️ Roadmap

- [x] Chrome extension with sidebar UI and loading animation
- [x] FastAPI backend with `/analyze` endpoint
- [x] Real repo context fetching via GitHub API
- [x] Deployed to Railway — live 24/7
- [x] GitHub App with automatic PR comment posting
- [x] Advanced prompt engineering for consistent, evidence-based verdicts
- [ ] Analysis caching (skip re-analyzing unchanged PRs)
- [ ] Per-repo risk rule configuration
- [ ] Web dashboard with PR history
- [ ] Chrome Web Store listing
- [ ] GitLab support

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Chrome Extension | Manifest V3, Vanilla JS |
| Backend | Python, FastAPI, Uvicorn |
| AI Model | Google Gemini 2.5 Flash |
| Repo Context | GitHub REST API |
| GitHub App Auth | PyJWT + RSA Private Key |
| Deployment | Railway |

---

## 🤝 Contributing

Contributions are welcome! Fork the repo, make your changes, and open a PR targeting `main`.

MergeIQ will automatically analyze your PR. Meta. 😄

---

## 📄 License

MIT — do whatever you want with it.

---

<div align="center">

<br/>

Built with ☕, persistence, and a lot of debugging.

**[⚡ MergeIQ](https://web-production-6f4dd.up.railway.app)** · Made by [primetree2](https://github.com/primetree2)

<br/>

</div>
