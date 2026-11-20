
import os
import uuid
import shutil
import ipaddress
import socket
from pathlib import Path
from urllib.parse import urlparse

import yt_dlp

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

ALLOWED_DOMAINS = {
    "youtube.com",
    "www.youtube.com",
    "youtu.be",
    "m.youtube.com",
    "facebook.com",
    "www.facebook.com",
    "m.facebook.com",
    "fb.watch",
    "instagram.com",
    "www.instagram.com",
}


@app.get("/")
def home():
    return {
        "message": "ClipMaster AI Backend Running",
        "status": "success"
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


def validate_video_url(url):
    try:
        parsed = urlparse(url)

        if parsed.scheme != "https":
            raise ValueError("Only HTTPS links are allowed")

        host = (parsed.hostname or "").lower()

        if host not in ALLOWED_DOMAINS:
            raise ValueError(
                "Only YouTube, Facebook and Instagram links are supported"
            )

        # Reject addresses resolving to private or local networks.
        addresses = socket.getaddrinfo(host, 443)
        for address in addresses:
            ip = ipaddress.ip_address(address[4][0])
            if not ip.is_global:
                raise ValueError("This video URL is not allowed")

    except ValueError:
        raise
    except Exception:
        raise ValueError("Invalid or unreachable video URL")


def download_video(url, output_path):
    options = {
        "format": "best[ext=mp4]/best",
        "outtmpl": str(output_path),
        "merge_output_format": "mp4",
        "noplaylist": True,
        "max_filesize": 1024 * 1024 * 1024,
        "socket_timeout": 30,
        "retries": 2,
        "quiet": True,
        "no_warnings": True,
    }

    with yt_dlp.YoutubeDL(options) as downloader:
        downloader.download([url])

    if not output_path.exists():
        alternatives = list(output_path.parent.glob(
            output_path.stem + ".*"
        ))
        if alternatives:
            return alternatives[0]

        raise ValueError("Video download failed")

    return output_path


def process_video(input_path, job_id):
    job_output = OUTPUT_DIR / job_id

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

    try:
        with input_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        return process_video(input_path, job_id)

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Video processing failed: {str(error)}"
        )

    finally:
        file.file.close()
        if input_path.exists():
            input_path.unlink()


@app.post("/api/create-shorts-from-url")
def create_shorts_from_url(data: dict):
    url = str(data.get("url", "")).strip()

    if not url:
        raise HTTPException(
            status_code=400,
            detail="Please provide a video URL"
        )

    try:
        validate_video_url(url)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))

    job_id = uuid.uuid4().hex
    input_path = UPLOAD_DIR / f"{job_id}.mp4"

    try:
        download_video(url, input_path)
        return process_video(input_path, job_id)

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Video link processing failed: {str(error)}"
        )

    finally:
        if input_path.exists():
            input_path.unlink()
            
