"""
SpecGen AI — AI Client Service
Sends extracted keyframes to Claude Vision and generates structured QA outputs:
1. Feature Summary
2. Manual Test Cases
3. Step-by-Step Action Log
4. Playwright TypeScript Script

The prompt engineering in this file is the core IP of the product.
"""

import anthropic
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# --- Model Configuration ---
DEFAULT_MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS = 12000

# --- Supported Frameworks (V2: add selenium, cypress, etc.) ---
FRAMEWORKS = {
    "playwright": {
        "name": "Playwright",
        "language": "TypeScript",
        "extension": ".spec.ts",
        "import_style": "import { test, expect } from '@playwright/test';",
    },
    # Future frameworks:
    # "selenium": { "name": "Selenium", "language": "Python", ... },
    # "cypress": { "name": "Cypress", "language": "JavaScript", ... },
}


def _build_system_prompt(framework: str = "playwright") -> str:
    """
    Build the system prompt for Claude Vision.
    This is the most important prompt in the entire application.
    """
    fw = FRAMEWORKS.get(framework, FRAMEWORKS["playwright"])

    return f"""You are SpecGen AI — a Senior SDET and QA Architect with 10+ years of experience.

You will receive a sequence of screenshots extracted from a screen recording of a web application walkthrough. These screenshots represent moments where the UI visually changed (page navigations, clicks, form fills, modals, etc.).

Your job is to analyze these screenshots and produce FOUR structured outputs. Be thorough, professional, and precise.

ANALYSIS RULES:
- Examine every screenshot carefully. Note URLs in the address bar, page titles, button labels, form fields, navigation elements, error messages, and any visible text.
- Infer the user's intent from the sequence of UI states. What workflow are they demonstrating?
- When you see a login/auth screen, NEVER hardcode credentials. Always use environment variables.
- When you're uncertain about a selector, use a clear TODO comment rather than guessing wrong.
- Prioritize accessible selectors: getByRole > getByLabel > getByText > getByPlaceholder > getByTestId('TODO-verify')
- If you can see URLs in the address bar, extract and use them.
- Pay attention to state changes between screenshots — what action likely happened between frame N and frame N+1?

OUTPUT FORMAT:
You must respond with a valid JSON object (no markdown, no backticks, no preamble) with exactly these four keys:

{{
  "feature_summary": "A 2-3 paragraph description of the feature/workflow shown...",

  "manual_test_cases": {{
    "positive_happy_path": [
      {{
        "id": "HP-001",
        "title": "Descriptive test case title",
        "category": "positive_happy_path",
        "priority": "High",
        "preconditions": ["User is logged in", "..."],
        "steps": [
          {{ "step": 1, "action": "Navigate to...", "expected": "Page loads with..." }}
        ],
        "postconditions": ["State after test..."],
        "confidence": "high|medium|low"
      }}
    ],
    "smoke_sanity": [ ... ],
    "negative_security": [ ... ],
    "e2e_workflow": [ ... ],
    "ui_ux_validation": [ ... ],
    "suggested_edge_cases": [ ... ]
  }},

  "action_log": [
    {{
      "step": 1,
      "timestamp": "0.0s",
      "action": "User navigates to login page",
      "ui_element": "Browser address bar",
      "observation": "Login form with email and password fields is displayed"
    }}
  ],

  "playwright_script": "The complete {fw['name']} {fw['language']} test script as a single string with proper newlines"
}}

=== CRITICAL: TEST CASE BUDGET & PRIORITY ALLOCATION ===

You have a MAXIMUM of 20 test cases total across ALL categories. Allocate them using this strict precedence order:

1. POSITIVE / HAPPY PATH (allocate FIRST, up to 10-12 cases)
   - These directly mirror the workflow shown in the video
   - Cover every meaningful user action demonstrated
   - This is the highest-value output — be thorough here

2. SMOKE / SANITY (allocate SECOND, only cases NOT already covered by happy path)
   - Bare minimum checks: page loads, key elements visible, basic functionality works
   - SKIP any test that would duplicate a happy path case
   - If the happy path already covers sanity scenarios, this section can be EMPTY

3. NEGATIVE & SECURITY (allocate THIRD, 3-5 cases)
   - Invalid inputs, empty required fields, wrong credentials, unauthorized access
   - Common security patterns: XSS in text fields, SQL injection in inputs, exceeding max length
   - Mark each with "confidence": "medium" or "low" since you're inferring from UI patterns

4. E2E WORKFLOW (allocate FOURTH, 1-2 cases)
   - The complete user journey from start to finish as ONE test case with many steps
   - Only if the video shows a multi-step workflow worth chaining

5. UI/UX VALIDATION (allocate FIFTH, 1-3 cases)
   - Layout consistency, element visibility, labels correct, responsive hints
   - Only include what you can actually verify from the screenshots

6. SUGGESTED EDGE CASES (fill remaining slots)
   - Boundary conditions, concurrent actions, timeout scenarios
   - Always mark with "confidence": "low" — these are educated guesses

IMPORTANT RULES FOR CATEGORY ALLOCATION:
- If a category has ZERO applicable test cases, set it to an EMPTY array []. Do NOT force-fit test cases into categories where they don't belong.
- NEVER duplicate the same test across categories. If "successful login" is in happy path, do NOT add it to smoke/sanity.
- Every test case MUST include a "confidence" field: "high" (directly observed in video), "medium" (reasonably inferred from UI), or "low" (educated guess based on common patterns).
- Count your total. If you've used 15 cases on happy path + sanity + negative, you only have 5 left for E2E + UI/UX + edge cases.

MANUAL TEST CASE REQUIREMENTS:
- Each test case must be independently executable
- Preconditions should include auth state, test data needs, and environment requirements
- Expected results must be specific and verifiable, not vague
- Each step should have a clear action and a clear expected result
- IDs follow the pattern: HP-001 (happy path), SM-001 (smoke), NG-001 (negative), E2E-001, UI-001, EC-001 (edge case)

PLAYWRIGHT SCRIPT REQUIREMENTS:
- Start with: {fw['import_style']}
- Organize tests into test.describe() blocks matching the categories:
    test.describe('Happy Path', () => {{ ... }});
    test.describe('Smoke / Sanity', () => {{ ... }});  // only if non-empty
    test.describe('Negative Scenarios', () => {{ ... }});
    test.describe('E2E: Full Workflow', () => {{ ... }});
- Add a test.beforeEach() for common setup (navigation, auth)
- For login flows: use process.env.TEST_USERNAME and process.env.TEST_PASSWORD
- Add meaningful test names that describe the behavior being tested
- Include await expect() assertions after every significant action
- Add comments explaining what each section does and its confidence level
- Use proper waits: await page.waitForLoadState('networkidle') after navigations
- Mark uncertain selectors with // TODO: verify selector
- If a URL is visible in screenshots, use it. Otherwise use a placeholder: 'https://YOUR_APP_URL'
- Add a comment block at the top explaining setup requirements
- Suggest page.context().storageState() for auth reuse if login is detected
- Mirror the test case budget: more happy path tests, fewer edge cases
- SKIP empty describe blocks — if no smoke tests, don't include the block

FEATURE SUMMARY REQUIREMENTS:
- Write it like a QA engineer describing the feature to a developer
- Include: what the feature does, the user workflow, key UI elements involved
- Mention any potential risk areas you notice (complex forms, multi-step flows, etc.)
- Note what types of testing are most relevant for this feature

ACTION LOG REQUIREMENTS:
- One entry per detected UI change (per screenshot transition)
- Include what likely user action caused the change
- Note any UI elements that appeared, disappeared, or changed state"""


def _build_messages(keyframes: list[dict]) -> list[dict]:
    """Build the messages array with keyframe images for Claude Vision."""
    content = []

    # Intro text
    content.append({
        "type": "text",
        "text": (
            f"I have {len(keyframes)} screenshots from a screen recording of a web application "
            f"walkthrough. They are in chronological order. Each screenshot represents a moment "
            f"where the UI visually changed. Analyze them and produce the structured QA outputs "
            f"as specified in your instructions.\n\n"
            f"Screenshots follow in order:"
        )
    })

    # Add each keyframe as an image with context
    for i, kf in enumerate(keyframes):
        content.append({
            "type": "text",
            "text": f"\n--- Screenshot {i + 1}/{len(keyframes)} | Timestamp: {kf['timestamp']}s ---"
        })
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/jpeg",
                "data": kf['base64']
            }
        })

    # Closing instruction
    content.append({
        "type": "text",
        "text": (
            "\n\nNow analyze all screenshots above and generate the complete JSON output "
            "with all four sections: feature_summary, manual_test_cases, action_log, "
            "and playwright_script. Remember: respond ONLY with valid JSON, no markdown "
            "backticks or preamble."
        )
    })

    return [{"role": "user", "content": content}]


def generate_spec(
    keyframes: list[dict],
    api_key: str,
    framework: str = "playwright",
    model: Optional[str] = None
) -> dict:
    """
    Send keyframes to Claude Vision and get structured QA outputs.

    Args:
        keyframes: List of keyframe dicts from video_processor
        api_key: User's Anthropic API key (BYOK)
        framework: Target test framework (default: playwright)
        model: Claude model to use (default: claude-sonnet-4)

    Returns:
        Dict with feature_summary, manual_test_cases, action_log, playwright_script

    Raises:
        SpecGenerationError: If API call or parsing fails
    """
    model = model or DEFAULT_MODEL
    client = anthropic.Anthropic(api_key=api_key)

    logger.info(
        f"Sending {len(keyframes)} keyframes to {model} "
        f"for {framework} spec generation"
    )

    try:
        response = client.messages.create(
            model=model,
            max_tokens=MAX_TOKENS,
            system=_build_system_prompt(framework),
            messages=_build_messages(keyframes),
            temperature=0.2,  # Low temperature for consistent, precise output
        )

        # Extract text from response
        raw_text = ""
        for block in response.content:
            if block.type == "text":
                raw_text += block.text

        # Clean up common JSON issues
        raw_text = raw_text.strip()
        if raw_text.startswith("```json"):
            raw_text = raw_text[7:]
        if raw_text.startswith("```"):
            raw_text = raw_text[3:]
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3]
        raw_text = raw_text.strip()

        # Parse JSON
        try:
            result = json.loads(raw_text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.error(f"Raw response (first 500 chars): {raw_text[:500]}")
            raise SpecGenerationError(
                "The AI returned an invalid response. This can happen with complex "
                "videos. Please try again or use a shorter recording."
            ) from e

        # Validate expected keys
        required_keys = ["feature_summary", "manual_test_cases", "action_log", "playwright_script"]
        missing = [k for k in required_keys if k not in result]
        if missing:
            raise SpecGenerationError(
                f"AI response is missing sections: {', '.join(missing)}. "
                f"Please try again."
            )

        # Add metadata
        result["_metadata"] = {
            "model": model,
            "framework": framework,
            "keyframes_processed": len(keyframes),
            "usage": {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            }
        }

        logger.info(
            f"Generation complete. Tokens used: "
            f"{response.usage.input_tokens} in / {response.usage.output_tokens} out"
        )

        return result

    except anthropic.AuthenticationError:
        raise SpecGenerationError(
            "Invalid API key. Please check your Anthropic API key and try again. "
            "You can get one at console.anthropic.com"
        )
    except anthropic.RateLimitError:
        raise SpecGenerationError(
            "API rate limit reached. Please wait a moment and try again."
        )
    except anthropic.APIError as e:
        logger.error(f"Anthropic API error: {e}")
        raise SpecGenerationError(
            f"API error: {str(e)}. Please try again."
        ) from e


class SpecGenerationError(Exception):
    """Raised when spec generation fails."""
    pass
