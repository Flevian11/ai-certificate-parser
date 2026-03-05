import os
from pathlib import Path

import pdfplumber
import pytesseract
from PIL import Image

# Ensure pytesseract knows where tesseract is (Windows-safe)
TESSERACT_EXE = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
if os.path.exists(TESSERACT_EXE):
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_EXE


def extract_text(file_path: str) -> str:
    ext = Path(file_path).suffix.lower()
    if ext == ".pdf":
        return _extract_from_pdf(file_path)
    return _extract_from_image(file_path)


def _extract_from_pdf(pdf_path: str) -> str:
    parts = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            parts.append(page.extract_text() or "")
    return "\n".join(parts).strip()


def _extract_from_image(image_path: str) -> str:
    img = Image.open(image_path)
    return pytesseract.image_to_string(img).strip()