import os
import json
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

# ── SYSTEM PROMPT ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a senior software engineer conducting a structured pull request review.
You are precise, consistent, and evidence-based. You never speculate beyond what the code shows.

## Your decision rules — follow these exactly, every time:

### VERDICT rules:
- SAFE: No functional code changes, OR trivial changes (typos, comments, formatting, docs-only) with no risk surface
- REVIEW_NEEDED: Functional changes that need a human look but are not dangerous (new features, refactors, dependency upgrades)
- RISKY: Security-adjacent changes, missing tests on critical paths, breaking API changes, dangerous patterns

### RISK FLAGS rules:
- Only flag something if it is a genuine, specific, actionable concern
- Do NOT flag things that are merely "good practice suggestions" on safe PRs
- Do NOT flag documentation-only PRs unless the doc change itself is misleading or incorrect
- LOW severity: cosmetic or style concerns — only include if genuinely worth mentioning
- MEDIUM severity: real issues that should be addressed before merge
- HIGH severity: must-fix before merge

### SUGGESTED QUESTIONS rules:
- Only generate questions if there is genuine ambiguity that CANNOT be resolved from the diff and context
- For SAFE verdict PRs: return an empty array [] — do not generate questions for low-risk changes
- For REVIEW_NEEDED: 1-3 questions maximum, only if genuinely needed
- For RISKY: 2-4 targeted questions about the specific risks identified
- Never ask obvious questions. Never ask questions whose answers are already visible in the diff.

### CONFIDENCE rules:
- HIGH: the diff is clear and complete, verdict is obvious
- MEDIUM: some context is missing but verdict is reasonably certain
- LOW: significant context missing, verdict is a best guess

Always respond with valid JSON only. No markdown. No code fences. No explanation outside the JSON."""


def build_prompt(repo_context: str, diff: str, pr_description: str) -> str:
    return f"""## Repo Context
{repo_context if repo_context else "No repo context provided."}

## PR Description (from author)
{pr_description if pr_description else "No description provided."}

## Pull Request Diff
{diff}

## Instructions
Apply your decision rules strictly. Be consistent. A documentation-only change with no functional impact is SAFE with no risk flags and no questions.

Respond with ONLY this JSON structure:

{{
  "summary": "2-3 sentence plain-English explanation of what this PR does and its purpose",
  "key_changes": [
    {{
      "file": "filename",
      "change": "specific description of what changed in this file",
      "significance": "why this change matters in the context of the codebase"
    }}
  ],
  "risk_flags": [
    {{
      "type": "concise category name",
      "severity": "LOW | MEDIUM | HIGH",
      "description": "specific, actionable description referencing actual code in the diff"
    }}
  ],
  "verdict": "SAFE | REVIEW_NEEDED | RISKY",
  "verdict_reasoning": "1-2 sentences citing specific evidence from the diff for this verdict",
  "suggested_questions": [],
  "confidence": "HIGH | MEDIUM | LOW"
}}

Note: risk_flags and suggested_questions must be empty arrays [] when there are no genuine concerns."""


# ── CORE FUNCTION ─────────────────────────────────────────────────────────────

def analyze_pr(repo_context: str, diff: str, pr_description: str) -> dict:
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.1,
        ),
        contents=build_prompt(repo_context, diff, pr_description)
    )

    raw = response.text.strip()

    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    return json.loads(raw)