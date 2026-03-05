from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
import os, shutil
from pathlib import Path

from parser import extract_text
from ollama_client import llm_extract_json
from legal_generator import generate_verification_letter

app = FastAPI(title="AI Certificate Parser + Legal Doc Generator")

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

ALLOWED_EXT = {".pdf", ".png", ".jpg", ".jpeg", ".webp"}


@app.get("/")
def home():
    return {"status": "ok", "message": "Upload a certificate to /upload"}

@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/debug-text")
async def debug_text(file: UploadFile = File(...)):
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXT:
        return JSONResponse(status_code=400, content={"error": f"Unsupported file type: {ext}"})

    save_path = UPLOAD_DIR / file.filename
    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    raw_text = extract_text(str(save_path))
    return {"filename": file.filename, "text_preview": raw_text[:2000]}


@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXT:
        return JSONResponse(
            status_code=400,
            content={"error": f"Unsupported file type: {ext}. Use PDF or image."},
        )

    save_path = UPLOAD_DIR / file.filename
    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    raw_text = extract_text(str(save_path))

    extracted = llm_extract_json(raw_text)

    legal_doc = generate_verification_letter(extracted)

    return {
        "filename": file.filename,
        "extracted": extracted,
        "legal_document": legal_doc,
    }