// ── CONSTANTS ────────────────────────────────────────────────────────────────
const API_URL = "https://web-production-6f4dd.up.railway.app/analyze";
const SIDEBAR_ID = "mergeiq-sidebar";

// ── SCRAPE DIFF FROM GITHUB PAGE ─────────────────────────────────────────────
function scrapeDiff() {
  const diffLines = [];

  // Get file names from data-file-path attributes
  const filePathButtons = document.querySelectorAll("[data-file-path]");
  const filePaths = new Set();
  filePathButtons.forEach(el => {
    const path = el.getAttribute("data-file-path");
    if (path) filePaths.add(path);
  });

  // Add file headers
  filePaths.forEach(path => {
    diffLines.push(`diff --git a/${path} b/${path}`);
  });

  // Get all diff line rows
  const rows = document.querySelectorAll("tr.diff-line-row");

  rows.forEach(row => {
    // Each split-view row has left (deletion) and right (addition) cells
    // We only read left-side for deletions and right-side for additions
    // to avoid duplicates in split view

    const cells = row.querySelectorAll("td.diff-text-cell");

    cells.forEach(cell => {
      const code = cell.querySelector("code.diff-text");
      if (!code) return;

      const marker = code.querySelector(".diff-text-marker")?.innerText?.trim() || "";
      const inner = code.querySelector(".diff-text-inner");
      const lineText = inner ? inner.innerText : code.innerText;

      const isDeletion = code.classList.contains("deletion");
      const isAddition = code.classList.contains("addition");
      const isNeutral = !isDeletion && !isAddition;

      // For split view: skip right-side deletions and left-side additions
      // to avoid outputting every line twice
      const isLeftCell = cell.classList.contains("left-side-diff-cell");
      const isRightCell = cell.classList.contains("right-side-diff-cell");

      if (isDeletion && isLeftCell) {
        diffLines.push("-" + lineText);
      } else if (isAddition && isRightCell) {
        diffLines.push("+" + lineText);
      } else if (isNeutral && isLeftCell) {
        diffLines.push(" " + lineText);
      }
    });
  });

  return diffLines.join("\n");
}

// ── SCRAPE PR METADATA ────────────────────────────────────────────────────────
function scrapePRInfo() {
  const title =
    document.querySelector("bdi.js-issue-title")?.innerText ||
    document.querySelector(".js-issue-title")?.innerText ||
    document.querySelector("h1 bdi")?.innerText ||
    "";

  const body = document.querySelector(".comment-body")?.innerText || "";

  const parts = window.location.pathname.split("/");
  const repoName = parts.length >= 3 ? `${parts[1]}/${parts[2]}` : "unknown";

  return {
    title: title.trim(),
    body: body.trim(),
    repo: repoName,
  };
}

// ── BUILD & INJECT SIDEBAR ────────────────────────────────────────────────────
function createSidebar() {
  if (document.getElementById(SIDEBAR_ID)) return;

  const sidebar = document.createElement("div");
  sidebar.id = SIDEBAR_ID;
  sidebar.innerHTML = `
    <div id="mergeiq-header">
      <span id="mergeiq-logo">
        <img src="${chrome.runtime.getURL('icon48.png')}" width="22" height="22" style="vertical-align:middle;margin-right:8px;border-radius:6px;"/>
        Merge<span style="color:#86c464">IQ</span>
      </span>
      <button id="mergeiq-close">✕</button>
    </div>
    <div id="mergeiq-body">
      <button id="mergeiq-analyze-btn">Analyze this PR</button>

      <div id="mergeiq-loading">
        <div class="mergeiq-spinner"></div>
        <div class="mergeiq-loading-steps">
          <div class="mergeiq-loading-step" id="step-diff">
            <div class="mergeiq-step-icon">1</div>
            <span>Reading diff</span>
          </div>
          <div class="mergeiq-loading-step" id="step-context">
            <div class="mergeiq-step-icon">2</div>
            <span>Fetching repo context</span>
          </div>
          <div class="mergeiq-loading-step" id="step-ai">
            <div class="mergeiq-step-icon">3</div>
            <span>Analyzing with Gemini</span>
          </div>
          <div class="mergeiq-loading-step" id="step-done">
            <div class="mergeiq-step-icon">4</div>
            <span>Preparing results</span>
          </div>
        </div>
      </div>

      <div id="mergeiq-result" style="display:none;"></div>
    </div>
  `;
  document.body.appendChild(sidebar);

  document.getElementById("mergeiq-close").addEventListener("click", () => {
    sidebar.remove();
  });

  document.getElementById("mergeiq-analyze-btn").addEventListener("click", runAnalysis);
}

// ── RUN ANALYSIS ──────────────────────────────────────────────────────────────
async function runAnalysis() {
  const btn = document.getElementById("mergeiq-analyze-btn");
  const resultDiv = document.getElementById("mergeiq-result");
  const loadingDiv = document.getElementById("mergeiq-loading");

  // Reset UI
  btn.disabled = true;
  btn.textContent = "Analyzing...";
  resultDiv.style.display = "none";
  loadingDiv.classList.add("visible");

  // Reset steps
  ["step-diff", "step-context", "step-ai", "step-done"].forEach(id => {
    const el = document.getElementById(id);
    el.classList.remove("active", "done");
  });

  // Step 1 — reading diff
  setStep("step-diff", "active");
  const diff = scrapeDiff();
  const prInfo = scrapePRInfo();

  console.log("[MergeIQ] Scraped diff length:", diff.length);

  if (!diff || diff.trim().length < 5) {
    loadingDiv.classList.remove("visible");
    showError("Could not read the diff.\n\nMake sure you are on the 'Files changed' tab and the file is expanded.");
    btn.disabled = false;
    btn.textContent = "Analyze this PR";
    return;
  }

  setStep("step-diff", "done");

  // Step 2 — fetching context (happens server-side, simulate timing)
  setStep("step-context", "active");
  await delay(600);
  setStep("step-context", "done");

  // Step 3 — AI analysis
  setStep("step-ai", "active");

  try {
    const response = await fetch(API_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        diff: diff,
        repo_context: `Repository: ${prInfo.repo}\nPR Title: ${prInfo.title}`,
        pr_description: prInfo.body,
        repo_owner: prInfo.repo.split("/")[0],
        repo_name: prInfo.repo.split("/")[1],
      }),
    });

    if (!response.ok) throw new Error(`Server error: ${response.status}`);

    const data = await response.json();

    setStep("step-ai", "done");

    // Step 4 — preparing results
    setStep("step-done", "active");
    await delay(300);
    setStep("step-done", "done");
    await delay(200);

    loadingDiv.classList.remove("visible");
    showResult(data);

  } catch (err) {
    loadingDiv.classList.remove("visible");
    showError("Error: " + err.message + "\n\nMake sure the server is running.");
  }

  btn.disabled = false;
  btn.textContent = "Re-analyze";
}

function setStep(id, state) {
  const el = document.getElementById(id);
  if (!el) return;
  el.classList.remove("active", "done");
  if (state) el.classList.add(state);
  const icon = el.querySelector(".mergeiq-step-icon");
  if (icon) icon.textContent = state === "done" ? "✓" : el.id.replace("step-", "").replace("diff", "1").replace("context", "2").replace("ai", "3").replace("done", "4");
}

function delay(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

// ── RENDER RESULT ─────────────────────────────────────────────────────────────
function showResult(data) {
  const resultDiv = document.getElementById("mergeiq-result");

  const verdictColor = {
    SAFE: "#2ea043",
    REVIEW_NEEDED: "#d4a44c",
    RISKY: "#c46464",
  }[data.verdict] || "#888";

  const severityColor = { HIGH: "#c46464", MEDIUM: "#d4a44c", LOW: "#2ea043" };

  const riskHTML = data.risk_flags.length > 0
    ? data.risk_flags.map((flag) => `
        <div class="mergeiq-risk-item">
          <span class="mergeiq-severity" style="background:${severityColor[flag.severity]}20;color:${severityColor[flag.severity]};border:1px solid ${severityColor[flag.severity]}40">
            ${flag.severity}
          </span>
          <div>
            <div class="mergeiq-risk-type">${flag.type}</div>
            <div class="mergeiq-risk-desc">${flag.description}</div>
          </div>
        </div>
      `).join("")
    : `<div class="mergeiq-all-clear">✓ No risk flags detected</div>`;

  const changesHTML = data.key_changes.map((c) => `
    <div class="mergeiq-change-item">
      <code class="mergeiq-filename">${c.file}</code>
      <div class="mergeiq-change-desc">${c.change}</div>
    </div>
  `).join("");

  const questionsHTML = data.suggested_questions.length > 0
    ? data.suggested_questions.map((q, i) => `
        <div class="mergeiq-question">${i + 1}. ${q}</div>
      `).join("")
    : `<div class="mergeiq-no-questions">No questions needed — this PR is self-explanatory.</div>`;

  resultDiv.innerHTML = `
    <div class="mergeiq-verdict" style="border-color:${verdictColor};background:${verdictColor}15">
      <span class="mergeiq-verdict-label" style="color:${verdictColor}">${data.verdict.replace("_", " ")}</span>
      <span class="mergeiq-confidence">confidence: ${data.confidence}</span>
      <p class="mergeiq-verdict-reason">${data.verdict_reasoning}</p>
    </div>

    <div class="mergeiq-section">
      <div class="mergeiq-section-title">Summary</div>
      <p class="mergeiq-summary">${data.summary}</p>
    </div>

    <div class="mergeiq-section">
      <div class="mergeiq-section-title">Key Changes</div>
      ${changesHTML}
    </div>

    <div class="mergeiq-section">
      <div class="mergeiq-section-title">Risk Flags</div>
      ${riskHTML}
    </div>

    <div class="mergeiq-section">
      <div class="mergeiq-section-title">Questions to ask</div>
      ${questionsHTML}
    </div>
  `;

  resultDiv.style.display = "block";
}

function showError(msg) {
  const resultDiv = document.getElementById("mergeiq-result");
  resultDiv.innerHTML = `<div class="mergeiq-error">${msg}</div>`;
  resultDiv.style.display = "block";
}

// ── INIT ──────────────────────────────────────────────────────────────────────
let lastUrl = location.href;
const observer = new MutationObserver(() => {
  if (location.href !== lastUrl) {
    lastUrl = location.href;
    if (location.href.includes("/pull/")) {
      setTimeout(createSidebar, 1500);
    }
  }
});

observer.observe(document.body, { childList: true, subtree: true });

if (location.href.includes("/pull/")) {
  createSidebar();
}