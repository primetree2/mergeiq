import os
import json
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

# ── PROMPT ────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a senior software engineer reviewing a pull request.
You have deep context about the codebase provided to you.
Be precise, specific, and actionable in your analysis.
Never speculate beyond what the code shows — if uncertain, say so explicitly.
Always respond with valid JSON only. No markdown, no code fences, no explanation outside the JSON."""

def build_prompt(repo_context, diff, pr_description):
    return f"""## Repo Context
{repo_context}

## PR Description (from author)
{pr_description}

## Pull Request Diff
{diff}

## Your Task
Analyze this pull request and respond with ONLY a JSON object using exactly this structure:

{{
  "summary": "2-3 sentence plain-English explanation of what this PR does",
  "key_changes": [
    {{
      "file": "filename",
      "change": "what changed",
      "significance": "why it matters"
    }}
  ],
  "risk_flags": [
    {{
      "type": "category of risk",
      "severity": "LOW | MEDIUM | HIGH",
      "description": "specific actionable description of the risk"
    }}
  ],
  "verdict": "SAFE | REVIEW_NEEDED | RISKY",
  "verdict_reasoning": "1-2 sentences explaining the verdict",
  "suggested_questions": [
    "question to ask the PR author"
  ],
  "confidence": "HIGH | MEDIUM | LOW"
}}"""

# ── CORE FUNCTION (imported by main.py) ───────────────────────────────────────

def analyze_pr(repo_context: str, diff: str, pr_description: str) -> dict:
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.2,
        ),
        contents=build_prompt(repo_context, diff, pr_description)
    )

    raw = response.text.strip()

    # Strip code fences if Gemini adds them despite instructions
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    return json.loads(raw)