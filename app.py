from fastapi import FastAPI, UploadFile, File, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError

from pathlib import Path
import shutil
import uuid
import traceback
from datetime import datetime, timedelta
import secrets

from parser import extract_text
from ollama_client import llm_extract_json
from legal_generator import generate_verification_letter
from pdf_generator import generate_verification_pdf

app = FastAPI(title="AI Certificate Parser")

# -------------------------
# Paths / Folders
# -------------------------
BASE_DIR = Path(__file__).parent
UPLOAD_DIR = BASE_DIR / "uploads"
PDF_DIR = BASE_DIR / "generated_pdfs"
STATIC_DIR = BASE_DIR / "static"

UPLOAD_DIR.mkdir(exist_ok=True)
PDF_DIR.mkdir(exist_ok=True)
STATIC_DIR.mkdir(exist_ok=True)

# Serve static folder
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

ALLOWED_EXT = {".pdf", ".png", ".jpg", ".jpeg", ".webp"}
MIN_OCR_CHARS = 60  # too little extracted text => treat as OCR failure


# -------------------------
# Global JSON error handlers
# -------------------------
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "error": "VALIDATION_ERROR",
            "details": exc.errors(),
            "message": "Request validation failed.",
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # Always JSON (prevents frontend null/extracted errors)
    return JSONResponse(
        status_code=500,
        content={
            "error": "SERVER_ERROR",
            "message": str(exc),
        },
    )


# -------------------------
# Basic routes
# -------------------------
@app.get("/")
def home():
    return {"status": "ok", "message": "Open /ui for UI or /docs for API docs"}


@app.get("/ui")
def ui():
    index_path = STATIC_DIR / "index.html"
    if not index_path.exists():
        return JSONResponse(
            status_code=404,
            content={"error": "UI_NOT_FOUND", "message": "static/index.html not found"},
        )
    return FileResponse(str(index_path))


@app.get("/health")
def health():
    return {"status": "healthy"}


# -------------------------
# Debug OCR text
# -------------------------
@app.post("/debug-text")
async def debug_text(file: UploadFile = File(...)):
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXT:
        return JSONResponse(
            status_code=400,
            content={"error": "UNSUPPORTED_FILE", "message": f"Unsupported file type: {ext}"},
        )

    safe_name = Path(file.filename).name
    save_path = UPLOAD_DIR / safe_name

    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    raw_text = extract_text(str(save_path)) or ""
    return {"filename": safe_name, "text_preview": raw_text[:8000]}


# -------------------------
# Download PDF
# -------------------------
@app.get("/download/{doc_id}")
def download_pdf(doc_id: str):
    pdf_path = PDF_DIR / f"verification_{doc_id}.pdf"
    if not pdf_path.exists():
        return JSONResponse(
            status_code=404,
            content={"error": "PDF_NOT_FOUND", "message": "PDF not found"},
        )

    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        filename=f"verification_{doc_id}.pdf",
    )


# -------------------------
# Main pipeline
# -------------------------
@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    """
    Upload -> OCR -> LLM -> Legal Letter -> HELB-style PDF
    Always returns JSON with:
      filename, extracted, legal_document, pdf_url
    """
    response_payload = {
        "filename": None,
        "extracted": {},
        "legal_document": "",
        "pdf_url": None,
    }

    try:
        # Validate extension
        ext = Path(file.filename).suffix.lower()
        safe_name = Path(file.filename).name
        response_payload["filename"] = safe_name

        if ext not in ALLOWED_EXT:
            response_payload["extracted"] = {
                "error": "UNSUPPORTED_FILE",
                "message": f"Unsupported file type: {ext}. Use PDF or image.",
            }
            response_payload["legal_document"] = "UNSUPPORTED FILE: Cannot generate verification document."
            return JSONResponse(status_code=400, content=response_payload)

        # Save uploaded file
        save_path = UPLOAD_DIR / safe_name
        with open(save_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        # 1) OCR
        raw_text = extract_text(str(save_path)) or ""
        raw_text_clean = raw_text.strip()

        extracted = {"_raw_text": raw_text[:8000]}

        # If OCR failed, stop pipeline (NO dummy data)
        if len(raw_text_clean) < MIN_OCR_CHARS:
            extracted.update({
                "_ocr_failed": True,
                "error": "OCR_FAILED",
                "message": "OCR could not extract enough readable text. Try a clearer scan (higher quality, less blur/shadow).",
            })
            response_payload["extracted"] = extracted
            response_payload["legal_document"] = "OCR FAILED: Could not generate a verification document."
            response_payload["pdf_url"] = None
            return JSONResponse(status_code=200, content=response_payload)

        # 2) LLM extraction (safe, best-effort, no fabrication)
        try:
            llm_data = llm_extract_json(raw_text)
            if isinstance(llm_data, dict):
                extracted.update(llm_data)
            else:
                extracted["_llm_error"] = "LLM returned non-JSON/dict output"
        except Exception as e:
            extracted["_llm_error"] = str(e)

        # 3) System-generated reference/serial (always present)
        # Example: ACP-20260305-7A3F9C
        extracted["system_ref"] = "ACP-" + datetime.now().strftime("%Y%m%d") + "-" + secrets.token_hex(3).upper()

        # 4) Ensure issue_date & valid_until (Valid = Issue + 1 year)
        if not extracted.get("issue_date"):
            issue_dt = datetime.now()
            extracted["issue_date"] = issue_dt.strftime("%d-%m-%Y")
        else:
            # best effort parse dd-mm-YYYY
            try:
                issue_dt = datetime.strptime(str(extracted["issue_date"]).strip(), "%d-%m-%Y")
            except Exception:
                issue_dt = datetime.now()
                extracted["issue_date"] = issue_dt.strftime("%d-%m-%Y")

        if not extracted.get("valid_until"):
            extracted["valid_until"] = (issue_dt + timedelta(days=365)).strftime("%d-%m-%Y")

        # 5) System officer names (typed, not signatures)
        extracted["system_ceo"] = "Flevian Ahithopel"
        extracted["system_coo"] = "Yasmin Aaliyah"

        # Optional: set defaults for nicer certificate headers (only if missing)
        extracted.setdefault("issuing_body", "AI CERTIFICATE PARSER")
        extracted.setdefault("document_title", "Verification Certificate")

        # 6) Generate legal letter text (structured)
        legal_doc = generate_verification_letter(extracted)

        # 7) Generate PDF (HELB-style)
        doc_id = str(uuid.uuid4())
        pdf_path = PDF_DIR / f"verification_{doc_id}.pdf"
        pdf_url = None

        try:
            generate_verification_pdf(extracted, legal_doc, str(pdf_path))
            pdf_url = f"/download/{doc_id}"
        except Exception as e:
            extracted["_pdf_error"] = str(e)

        response_payload["extracted"] = extracted
        response_payload["legal_document"] = legal_doc
        response_payload["pdf_url"] = pdf_url

        return JSONResponse(status_code=200, content=response_payload)

    except Exception as e:
        # Always return JSON (so frontend never sees null)
        response_payload["extracted"] = {
            "error": "PIPELINE_ERROR",
            "message": str(e),
            "trace": traceback.format_exc()[:4000],
        }
        response_payload["legal_document"] = "SERVER ERROR: Could not generate verification document."
        response_payload["pdf_url"] = None
        return JSONResponse(status_code=500, content=response_payload)