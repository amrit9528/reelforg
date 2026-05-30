from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, field_validator
from typing import Optional
import uvicorn
import os
import uuid
import shutil
from pathlib import Path
from processor import VideoProcessor
from seo import generate_seo
from youtube_uploader import upload_to_youtube

app = FastAPI(title="ReelForge API")

# Allow requests from your EC2 domain/IP
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "./uploads"))
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "./outputs"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/outputs", StaticFiles(directory=str(OUTPUT_DIR)), name="outputs")

jobs = {}


class YouTubeRequest(BaseModel):
    url: str
    format: str = "both"
    max_shorts: int = 5
    mode: str = "best_shorts"
    clip_duration: int = 60

    @field_validator("url")
    @classmethod
    def validate_url(cls, v):
        if not v or not v.strip():
            raise ValueError("URL cannot be empty")
        return v

    @field_validator("format")
    @classmethod
    def validate_format(cls, v):
        if v not in ["vertical", "horizontal", "both"]:
            raise ValueError("format must be 'vertical', 'horizontal', or 'both'")
        return v

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, v):
        if v not in ["best_shorts", "equal_clips"]:
            raise ValueError("mode must be 'best_shorts' or 'equal_clips'")
        return v

    @field_validator("max_shorts")
    @classmethod
    def validate_max_shorts(cls, v):
        if v < 1 or v > 15:
            raise ValueError("max_shorts must be between 1 and 15")
        return v

    @field_validator("clip_duration")
    @classmethod
    def validate_clip_duration(cls, v):
        if v < 15 or v > 300:
            raise ValueError("clip_duration must be between 15 and 300 seconds")
        return v


class UploadRequest(BaseModel):
    format: str = "both"
    max_shorts: int = 5
    mode: str = "best_shorts"
    clip_duration: int = 60


class YTUploadRequest(BaseModel):
    job_id: str
    filename: str
    title: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[list] = None
    privacy: str = "private"        # "private" | "unlisted" | "public"


class SEORequest(BaseModel):
    job_id: str
    filename: str
    topic: Optional[str] = ""


class ExportSelectedRequest(BaseModel):
    job_id: str
    selected_indices: list
    format: str = "both"


@app.post("/api/process/youtube")
async def process_youtube(req: YouTubeRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    jobs[job_id] = {"status": "queued", "progress": 0, "message": "Queued...", "shorts": []}
    background_tasks.add_task(
        run_pipeline, job_id, None, req.url,
        req.format, req.max_shorts, req.mode, req.clip_duration
    )
    return {"job_id": job_id}


@app.post("/api/process/upload")
async def process_upload(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    format: str = "both",
    max_shorts: int = 5,
    mode: str = "best_shorts",
    clip_duration: int = 60,
):
    job_id = str(uuid.uuid4())
    ext = Path(file.filename).suffix
    save_path = UPLOAD_DIR / f"{job_id}{ext}"
    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    jobs[job_id] = {"status": "queued", "progress": 0, "message": "Uploaded. Starting...", "shorts": []}
    background_tasks.add_task(
        run_pipeline, job_id, str(save_path), None,
        format, max_shorts, mode, clip_duration
    )
    return {"job_id": job_id}


class FileURLRequest(BaseModel):
    url: str
    format: str = "both"
    max_shorts: int = 5
    mode: str = "best_shorts"
    clip_duration: int = 60

    @field_validator("url")
    @classmethod
    def validate_url(cls, v):
        if not v or not v.strip():
            raise ValueError("URL cannot be empty")
        return v

    @field_validator("format")
    @classmethod
    def validate_format(cls, v):
        if v not in ["vertical", "horizontal", "both"]:
            raise ValueError("format must be 'vertical', 'horizontal', or 'both'")
        return v

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, v):
        if v not in ["best_shorts", "equal_clips"]:
            raise ValueError("mode must be 'best_shorts' or 'equal_clips'")
        return v

    @field_validator("max_shorts")
    @classmethod
    def validate_max_shorts(cls, v):
        if v < 1 or v > 15:
            raise ValueError("max_shorts must be between 1 and 15")
        return v

    @field_validator("clip_duration")
    @classmethod
    def validate_clip_duration(cls, v):
        if v < 15 or v > 300:
            raise ValueError("clip_duration must be between 15 and 300 seconds")
        return v


@app.post("/api/process/url")
async def process_file_url(req: FileURLRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    jobs[job_id] = {"status": "queued", "progress": 0, "message": "Downloading video...", "shorts": []}
    background_tasks.add_task(
        run_pipeline, job_id, req.url, None,
        req.format, req.max_shorts, req.mode, req.clip_duration
    )
    return {"job_id": job_id}


@app.get("/api/status/health")
async def health_check():
    return {"status": "ok", "service": "ReelForge API"}


@app.get("/api/status/{job_id}")
async def get_status(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    j = jobs[job_id]
    return {"job_id": job_id, **j}


@app.post("/api/seo")
async def get_seo(req: SEORequest):
    """Generate AI SEO (title, description, tags) for a clip."""
    try:
        seo = await generate_seo(req.filename, req.topic)
        return seo
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/youtube/upload")
async def yt_upload(req: YTUploadRequest):
    """Upload a clip to YouTube."""
    job = jobs.get(req.job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    clip_path = OUTPUT_DIR / req.job_id / req.filename
    if not clip_path.exists():
        raise HTTPException(status_code=404, detail="Clip file not found")

    try:
        result = await upload_to_youtube(
            file_path=str(clip_path),
            title=req.title or req.filename,
            description=req.description or "",
            tags=req.tags or [],
            privacy=req.privacy,
        )
        # Update job shorts with YT url
        for s in job["shorts"]:
            if s["filename"] == req.filename:
                s["uploaded_to_yt"] = True
                s["yt_url"] = result.get("url")
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/export-selected")
async def export_selected(req: ExportSelectedRequest, background_tasks: BackgroundTasks):
    """Export only selected clips with specified format."""
    job = jobs.get(req.job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if "detected_segments" not in job:
        raise HTTPException(status_code=400, detail="No detected segments found. Run detection first.")

    # Update job to export status
    job["status"] = "exporting"
    job["progress"] = 0
    job["message"] = "Exporting selected clips..."

    background_tasks.add_task(
        export_selected_clips, req.job_id, req.selected_indices, req.format
    )
    return {"job_id": req.job_id}


async def run_pipeline(job_id, video_path, yt_url, format, max_shorts, mode, clip_duration):
    processor = VideoProcessor(
        job_id=job_id,
        video_path=video_path,
        yt_url=yt_url,
        output_dir=str(OUTPUT_DIR),
        format=format,
        max_shorts=max_shorts,
        mode=mode,
        clip_duration=clip_duration,
        jobs=jobs,
    )
    await processor.run(detection_only=True)


async def export_selected_clips(job_id, selected_indices, format):
    job = jobs[job_id]
    segments = job.get("detected_segments", [])

    if not segments:
        job["status"] = "error"
        job["message"] = "No segments found"
        return

    selected_segments = [segments[i] for i in selected_indices if i < len(segments)]

    processor = VideoProcessor(
        job_id=job_id,
        video_path=job.get("video_path"),
        yt_url=None,
        output_dir=str(OUTPUT_DIR),
        format=format,
        max_shorts=len(selected_segments),
        mode="custom",
        clip_duration=0,
        jobs=jobs,
    )
    await processor.export_clips(selected_segments)


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
