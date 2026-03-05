# AI Certificate Parser

AI-powered system that parses certificates and generates legal verification documents.

## Features

- Upload certificate (PDF / Image)
- OCR extraction using **Tesseract**
- AI structured data extraction using **Ollama LLM**
- Automatic **verification letter generation**
- Clean **FastAPI backend**
- Modern **UI dashboard**

## Architecture

Upload → OCR → AI Extraction → Structured JSON → Legal Document

## Tech Stack

- Python
- FastAPI
- Tesseract OCR
- Ollama (Local LLM)
- pdfplumber
- Tailwind UI

## Run Locally

```bash
uvicorn app:app --reload

Open UI:

http://127.0.0.1:8000/ui
Example Fields Extracted

Full Name

Institution

Certificate Number

Degree / Qualification

Issue Date