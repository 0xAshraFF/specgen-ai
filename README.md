# ⚡ SpecGen AI

**Turn screen recordings into test cases, documentation, and automation scripts — instantly.**

> Record a walkthrough. Get manual test cases, step-by-step action logs, feature documentation, and a Playwright TypeScript spec file. No more blank-page problem.

---

## The Problem

Every QA team has the same bottleneck: someone records a Loom or screen share demonstrating a feature, and then a QA engineer has to manually:

1. Watch the entire video (again)
2. Write the feature summary for documentation
3. Create manual test cases with steps and expected results
4. Write automated test scripts from scratch

This takes **hours per feature** — and it's entirely repetitive work.

## The Solution

SpecGen AI watches your screen recording and generates everything automatically:

| Output | Who It's For | What You Get |
|---|---|---|
| **Feature Summary** | PMs, Docs | A concise description of the workflow demonstrated |
| **Manual Test Cases** | QA Engineers | Structured test cases with IDs, steps, and expected results |
| **Action Log** | Developers, QA | Ordered list of every user action detected in the recording |
| **Playwright Script** | SDETs | A downloadable `.spec.ts` file ready for review and execution |

**Every output is copy-pasteable.** Feed them into Cursor, Claude Code, or your IDE to refine further.

---

## How It Works

```
Screen Recording (.mp4/.webm)
        │
        ▼
┌─────────────────┐
│  OpenCV + SSIM   │  ← Extracts only frames where the UI actually changed
│  Frame Extractor │
└────────┬────────┘
         │ keyframes (base64)
         ▼
┌─────────────────┐
│  Claude Vision   │  ← Analyzes screenshots as a Senior SDET would
│  (Sonnet 4)      │
└────────┬────────┘
         │ structured JSON
         ▼
┌─────────────────┐
│  Structured      │  → Feature Summary
│  QA Outputs      │  → Manual Test Cases
│                  │  → Action Log
│                  │  → Playwright .spec.ts
└─────────────────┘
```

**Key technical decisions:**
- **SSIM (Structural Similarity Index)** ensures we only send meaningful frames to the AI — not 120 identical screenshots of a loading spinner
- **BYOK (Bring Your Own Key)** — your Anthropic API key, your costs, nothing stored on any server
- **Framework-agnostic architecture** — Playwright today, Selenium/Cypress/Robot Framework coming next

---

## Quick Start

### Prerequisites

- Python 3.10+
- An Anthropic API key ([get one here](https://console.anthropic.com))

### Install & Run

```bash
# Clone
git clone https://github.com/0xAshraFF/specgen-ai.git
cd specgen-ai

# Install dependencies
pip install -r requirements.txt

# Run
python main.py
```

Open **http://localhost:8000** in your browser. That's it.

### Usage

1. Paste your Anthropic API key
2. Upload a screen recording (MP4/WEBM, under 2 minutes)
3. Click **Generate Test Cases**
4. Copy outputs or download the `.spec.ts` file

---

## What You Get (Example Output)

<details>
<summary><strong>📋 Manual Test Case (sample)</strong></summary>

```
TC-001: Verify successful login with valid credentials
Priority: High
Preconditions:
  - User account exists with valid credentials
  - User is on the login page

Steps:
  1. Enter valid email in the email field
     Expected: Email is displayed in the input
  2. Enter valid password in the password field
     Expected: Password is masked
  3. Click the "Sign In" button
     Expected: User is redirected to the dashboard

Postconditions:
  - User session is active
  - Dashboard displays user-specific data
```
</details>

<details>
<summary><strong>🎭 Playwright Script (sample)</strong></summary>

```typescript
import { test, expect } from '@playwright/test';

test.describe('Login Feature', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(process.env.BASE_URL || 'https://YOUR_APP_URL');
    await page.waitForLoadState('networkidle');
  });

  test('should login with valid credentials', async ({ page }) => {
    await page.getByLabel('Email').fill(process.env.TEST_USERNAME || '');
    await page.getByLabel('Password').fill(process.env.TEST_PASSWORD || '');
    await page.getByRole('button', { name: 'Sign In' }).click();
    await page.waitForLoadState('networkidle');
    await expect(page.getByRole('heading', { name: /dashboard/i })).toBeVisible();
  });
});
```
</details>

---

## Cost

SpecGen AI uses the **BYOK (Bring Your Own Key)** model. You use your own Anthropic API key.

| Video Length | Keyframes | Approx. Cost |
|---|---|---|
| 30 seconds | 3-5 frames | ~$0.01-0.03 |
| 1 minute | 5-10 frames | ~$0.03-0.06 |
| 2 minutes | 10-20 frames | ~$0.05-0.10 |

Costs are per generation, paid to Anthropic. SpecGen AI itself is free and open source.

---

## Limitations (Alpha)

This is an **alpha release** — here's what to expect:

- Generated Playwright scripts are a **strong first draft**, not push-button automation. Selectors are inferred from screenshots and may need manual verification.
- Works best with **short, focused recordings** of a single user workflow.
- Currently supports **Playwright TypeScript only** (Selenium, Cypress coming in V2).
- Video must be **under 2 minutes** and **under 100MB**.
- The AI can see what's on screen but **cannot access the DOM** — so some selectors will be marked with `// TODO: verify`.

---

## Roadmap

- [x] Core pipeline: Video → Keyframes → Claude Vision → Structured output
- [x] Playwright TypeScript generation
- [x] Manual test case generation
- [x] Feature summary + action log
- [ ] Selenium (Python) support
- [ ] Cypress (JavaScript) support
- [ ] Robot Framework support
- [ ] DOM-aware mode (provide URL for real selector extraction)
- [ ] Browser extension for simultaneous video + DOM capture
- [ ] Batch processing (multiple videos)
- [ ] Export to Jira/TestRail format

---

## Architecture

```
specgen-ai/
├── main.py                        # FastAPI app + routes
├── services/
│   ├── video_processor.py         # OpenCV SSIM keyframe extraction
│   └── ai_client.py               # Claude Vision prompt engineering
├── index.html                     # Single-page dark-mode UI
├── requirements.txt               # Python dependencies
└── README.md
```

Built with: **FastAPI** • **OpenCV** • **scikit-image** • **Anthropic Claude Vision** • **Vanilla JS**

---

## Contributing

Found a bug? Have an idea? Open an [issue](https://github.com/0xAshraFF/specgen-ai/issues) or submit a PR.

This project is in early alpha — feedback from QA engineers is incredibly valuable.

---

## License

MIT

---

<p align="center">
  Built by <a href="https://github.com/0xAshraFF">@0xAshraFF</a> — QA Engineer building tools for QA Engineers
</p>
