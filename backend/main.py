
import os
import uuid
import shutil
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from video_processor import create_shorts

app = FastAPI(title="ClipMaster AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "outputs"

UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

app.mount(
    "/outputs",
    StaticFiles(directory=str(OUTPUT_DIR)),
    name="outputs"
)


@app.get("/")
def home():
    return {
        "message": "ClipMaster AI Backend Running",
        "status": "success"
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/api/create-shorts")
def create_video_shorts(file: UploadFile = File(...)):
    allowed = {".mp4", ".mov", ".mkv", ".webm"}

    extension = Path(file.filename or "").suffix.lower()

    if extension not in allowed:
        raise HTTPException(
            status_code=400,
            detail="Unsupported video format"
        )

    job_id = uuid.uuid4().hex
    input_path = UPLOAD_DIR / f"{job_id}{extension}"
    job_output = OUTPUT_DIR / job_id

    try:
        with input_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        results = create_shorts(
            str(input_path),
            output_dir=str(job_output),
            clip_seconds=30,
            max_shorts=3
        )

        return {
            "status": "success",
            "message": "Shorts created successfully",
            "shorts": [
                f"/outputs/{job_id}/{Path(path).name}"
                for path in results
            ]
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Video processing failed: {str(error)}"
        )

    finally:
        file.file.close()
        if input_path.exists():
            input_path.unlink()
            
