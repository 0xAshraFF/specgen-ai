"""
SpecGen AI — Main Application
FastAPI backend that orchestrates video processing and AI-powered test generation.

Usage:
    pip install -r requirements.txt
    python main.py

Then open http://localhost:8000 in your browser.
"""

import os
import uuid
import shutil
import logging
import tempfile
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, UploadFile, Header, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from services.video_processor import extract_keyframes, get_video_info, VideoProcessingError
from services.ai_client import generate_spec, SpecGenerationError

# --- Logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("specgen")

# --- Temp directory for uploaded videos ---
TEMP_DIR = Path(tempfile.gettempdir()) / "specgen_uploads"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    TEMP_DIR.mkdir(exist_ok=True)
    logger.info(f"SpecGen AI started. Temp dir: {TEMP_DIR}")
    yield
    # Cleanup temp files on shutdown
    if TEMP_DIR.exists():
        shutil.rmtree(TEMP_DIR, ignore_errors=True)
        logger.info("Cleaned up temp directory.")


# --- App ---
app = FastAPI(
    title="SpecGen AI",
    description="AI-powered test generation from screen recordings",
    version="0.1.0-alpha",
    lifespan=lifespan,
)

# CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Models ---
class HealthResponse(BaseModel):
    status: str
    version: str


class ErrorResponse(BaseModel):
    error: str
    detail: str


# --- Routes ---

@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    """Serve the single-page frontend."""
    index_path = Path(__file__).parent / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="Frontend not found")
    return HTMLResponse(content=index_path.read_text(encoding="utf-8"))


@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "version": "0.1.0-alpha"}


@app.post("/api/generate")
async def generate_test(
    video: UploadFile = File(..., description="Screen recording (MP4/WEBM, max 2 min)"),
    x_api_key: str = Header(..., description="Your Anthropic API key"),
    x_model: str = Header(
        default="claude-sonnet-4-20250514",
        description="Claude model to use"
    ),
    x_framework: str = Header(
        default="playwright",
        description="Target test framework"
    ),
):
    """
    Main endpoint: Upload a video, get test cases and automation scripts.

    - Accepts MP4/WEBM video files (max 2 minutes)
    - Requires an Anthropic API key (BYOK — your key, your costs)
    - Returns: feature summary, manual test cases, action log, Playwright script
    """
    # --- Validate file type ---
    allowed_types = {
        "video/mp4", "video/webm", "video/quicktime",
        "video/x-msvideo", "video/x-matroska"
    }
    if video.content_type and video.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {video.content_type}. "
                   f"Please upload MP4 or WEBM."
        )

    # --- Validate API key format ---
    if not x_api_key or not x_api_key.startswith("sk-ant-"):
        raise HTTPException(
            status_code=400,
            detail="Invalid API key format. Anthropic keys start with 'sk-ant-'. "
                   "Get yours at console.anthropic.com"
        )

    # --- Save temp file ---
    file_id = str(uuid.uuid4())
    suffix = Path(video.filename).suffix if video.filename else ".mp4"
    temp_path = TEMP_DIR / f"{file_id}{suffix}"

    try:
        with open(temp_path, "wb") as f:
            content = await video.read()
            # Basic size check (~100MB limit)
            if len(content) > 100 * 1024 * 1024:
                raise HTTPException(
                    status_code=400,
                    detail="File too large. Maximum size is 100MB."
                )
            f.write(content)

        logger.info(f"Processing video: {video.filename} ({len(content) / 1024 / 1024:.1f}MB)")

        # --- Step 1: Extract keyframes ---
        try:
            keyframes = extract_keyframes(str(temp_path))
        except VideoProcessingError as e:
            raise HTTPException(status_code=422, detail=str(e))

        logger.info(f"Extracted {len(keyframes)} keyframes")

        # --- Step 2: Generate specs via Claude Vision ---
        try:
            result = generate_spec(
                keyframes=keyframes,
                api_key=x_api_key,
                framework=x_framework,
                model=x_model,
            )
        except SpecGenerationError as e:
            raise HTTPException(status_code=422, detail=str(e))

        # --- Step 3: Return structured response ---
        return JSONResponse(content={
            "success": True,
            "data": result,
            "video_info": {
                "filename": video.filename,
                "keyframes_extracted": len(keyframes),
            }
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error processing {video.filename}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal error: {str(e)}. Please try again."
        )
    finally:
        # Always clean up the temp file
        if temp_path.exists():
            temp_path.unlink()
            logger.debug(f"Cleaned up temp file: {temp_path}")


@app.post("/api/preview")
async def preview_keyframes(
    video: UploadFile = File(..., description="Screen recording to preview"),
):
    """
    Preview endpoint: See video info and keyframe count before generating.
    Doesn't require an API key — no AI calls are made.
    """
    file_id = str(uuid.uuid4())
    suffix = Path(video.filename).suffix if video.filename else ".mp4"
    temp_path = TEMP_DIR / f"{file_id}{suffix}"

    try:
        with open(temp_path, "wb") as f:
            content = await video.read()
            f.write(content)

        info = get_video_info(str(temp_path))
        keyframes = extract_keyframes(str(temp_path))

        return JSONResponse(content={
            "success": True,
            "video_info": info,
            "keyframes_found": len(keyframes),
            "estimated_cost": f"~${len(keyframes) * 0.005:.3f} USD",
        })

    except VideoProcessingError as e:
        raise HTTPException(status_code=422, detail=str(e))
    finally:
        if temp_path.exists():
            temp_path.unlink()


# --- Run ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
