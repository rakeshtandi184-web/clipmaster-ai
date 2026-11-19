
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="ClipMaster AI",
    description="AI Automatic Shorts Creator",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {
        "message": "ClipMaster AI Backend is Running!",
        "status": "success"
    }

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "app": "ClipMaster AI"
    }
  
