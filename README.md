# AI Certificate Parser & Legal Document Generator

This project demonstrates an AI-powered pipeline for parsing academic certificates and generating verification documents.

## Features

- Upload certificate PDF or image
- Extract text using OCR (Tesseract)
- Use local LLM (Ollama) to extract structured data
- Generate legal verification documents automatically

## Tech Stack

FastAPI  
Python  
Tesseract OCR  
Ollama (Local LLM)  
pdfplumber

## Architecture

Upload → OCR → LLM Extraction → Structured JSON → Legal Document Generation

## Example Fields Extracted

- Full Name
- Institution
- Degree / Certificate
- Certificate Number
- Issue Date
- Issuing Body

## Run Locally

```bash
uvicorn app:app --reload

Then open:

http://127.0.0.1:8000/docs

Upload a certificate using the /upload endpoint.