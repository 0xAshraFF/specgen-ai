# SpecGen AI — Project Memory

## Problem Statement

QA teams spend significant time manually documenting test cases and writing automation scripts after watching developers or product teams walk through features. This creates a bottleneck: recordings of workflows exist, but converting them into structured test artifacts is slow, repetitive, and error-prone.

**SpecGen AI solves this by turning screen recordings into structured QA outputs automatically** — no manual transcription, no copy-pasting steps from video into spreadsheets.

---

## What We Built (v0.1.0-alpha)

### Core Pipeline

```
Screen Recording (MP4/WEBM)
  → OpenCV keyframe extraction (SSIM-based, filters duplicate frames)
  → Claude Vision API (sends base64 keyframes)
  → Structured JSON output
  → Frontend display (tabs: Feature Summary, Test Cases, Action Log, Script)
```

### Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI (Python) |
| Video Processing | OpenCV + scikit-image (SSIM) |
| AI | Anthropic Claude Vision API (BYOK) |
| Frontend | Vanilla HTML/CSS/JS (single file, no build step) |
| Validation | Pydantic |

### Implemented Features

**Video Processing**
- SSIM-based keyframe extraction — only frames where the UI meaningfully changed
- Configurable SSIM threshold (default 0.85)
- 1 FPS sampling before SSIM filtering
- Frame resize to 1024px width for consistent processing
- Video validation: 2–120 seconds, max 100MB, MP4/WEBM/MOV/MKV

**AI Generation**
- Claude Vision analyzes keyframes (sent as base64 JPEG)
- Prompt engineered for a "Senior SDET with 10+ years experience" persona
- Generates 4 structured outputs per recording:
  1. **Feature Summary** — 2-3 paragraph workflow description
  2. **Manual Test Cases** — up to 20 cases, categorized (happy path, smoke, negative, E2E, UI/UX, edge cases), with priority badges and confidence scores
  3. **Action Log** — timestamped chronological user actions
  4. **Playwright TypeScript script** — `.spec.ts` ready to run
- Structured JSON response parsing with graceful fallback
- Token budget: 12,000 max output tokens, temperature 0.2
- Selector strategy: `getByRole` > `getByLabel` > `getByText` > `getByPlaceholder` > `getByTestId`
- Uncertain selectors marked with `// TODO:` for manual verification

**API**
- `GET /` — serves frontend
- `GET /api/health` — health check
- `POST /api/generate` — main pipeline (upload → generate)
- `POST /api/preview` — extract keyframes only (no API key needed)
- Model and framework selection via HTTP headers (`x-model`, `x-framework`)
- CORS enabled for local dev

**Frontend**
- Drag-and-drop + click-to-upload
- API key input (password field, never stored)
- Model selector (claude-sonnet-4, claude-sonnet-4-5)
- Framework selector (Playwright only in v0.1)
- Tabbed results view with copy-to-clipboard for each section
- Download `.spec.ts` button
- Progress bar with status messages
- Metadata panel (model used, keyframes extracted, tokens consumed, test count)
- Dark mode, responsive layout

**Privacy Model (BYOK)**
- Users provide their own Anthropic API key in the UI
- Key is sent only to Anthropic — never stored on SpecGen servers
- No backend secrets required to deploy

---

## Current Limitations (Known)

- Playwright TypeScript is the only output framework
- AI infers selectors from screenshots — cannot read actual DOM, so selectors may need manual adjustment
- Best results with short, focused recordings of a single workflow (< 2 min)
- No user accounts, no history, no batch processing
- Single HTML file frontend — no component architecture yet

---

## Next Iterations (Roadmap)

### Iteration 2 — Framework Expansion
- [ ] Add **Selenium (Python)** output
- [ ] Add **Cypress (JavaScript)** output
- [ ] Add **Robot Framework** output
- [ ] Framework-specific prompt engineering per target

### Iteration 3 — DOM-Aware Mode
- [ ] Accept a URL alongside the recording
- [ ] Scrape live DOM to extract real selectors (IDs, aria-labels, data-testids)
- [ ] Replace inferred selectors with verified ones — eliminate `// TODO:` comments
- [ ] Possibly: browser extension that captures video + DOM snapshot simultaneously

### Iteration 4 — Integrations & Export
- [ ] Export test cases to **Jira** (Xray test format)
- [ ] Export to **TestRail** format
- [ ] Export to **Notion** page
- [ ] Webhook support for CI/CD trigger after generation

### Iteration 5 — Batch & Scale
- [ ] Batch processing (upload multiple recordings, process queue)
- [ ] Session history (store past generations locally or in cloud)
- [ ] Side-by-side diff view when a recording updates an existing flow
- [ ] Team sharing / shareable links

### Iteration 6 — Quality & Confidence
- [ ] Auto-run generated Playwright script in sandboxed browser, report selector failures
- [ ] Confidence score threshold setting (filter out low-confidence tests)
- [ ] User feedback loop: mark tests as correct/incorrect to improve prompts
- [ ] Cost estimator before generation (show expected token cost)

---

## File Map

```
specgen-ai/
├── main.py                  # FastAPI app, routes, file handling
├── services/
│   ├── __init__.py
│   ├── video_processor.py   # OpenCV SSIM keyframe extraction
│   └── ai_client.py         # Claude Vision integration, prompt engineering
├── index.html               # Entire frontend (single file)
├── requirements.txt
├── README.md
└── CONTRIBUTING.md
```

## Key Constants (quick reference)

| Constant | Value | Location |
|---|---|---|
| SSIM threshold | 0.85 | video_processor.py |
| Sample FPS | 1 | video_processor.py |
| Max keyframes | 20 | video_processor.py |
| Max video duration | 120s | video_processor.py |
| Max file size | 100MB | main.py |
| Max output tokens | 12,000 | ai_client.py |
| Temperature | 0.2 | ai_client.py |
| Default model | claude-sonnet-4-20250514 | ai_client.py |
