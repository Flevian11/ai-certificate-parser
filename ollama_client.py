import json
import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "phi3"  # we'll pull this after install


def llm_extract_json(raw_text: str) -> dict:
    """
    Sends certificate text to Ollama and returns extracted fields as JSON dict.
    """
    prompt = f"""
You are a document information extraction system.

Extract structured data from the certificate text.

Return ONLY valid JSON with these fields:

{{
 "full_name": "",
 "institution": "",
 "degree_or_certificate": "",
 "certificate_number": "",
 "issue_date": "",
 "issuing_body": ""
}}

Rules:
- If a value is missing, return null
- issue_date must be formatted YYYY-MM-DD if possible
- Do NOT include explanations
- Only return JSON

Certificate text:
{raw_text}
""".strip()

    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False
    }

    r = requests.post(OLLAMA_URL, json=payload, timeout=120)
    r.raise_for_status()

    data = r.json()
    text = (data.get("response") or "").strip()

    # Try to parse JSON safely (handles cases where model adds junk)
    return _safe_json(text)


def _safe_json(s: str) -> dict:
    # Extract first JSON object if extra text sneaks in
    start = s.find("{")
    end = s.rfind("}")
    if start != -1 and end != -1 and end > start:
        s = s[start:end + 1]

    try:
        return json.loads(s)
    except Exception:
        # fallback minimal response
        return {
            "full_name": None,
            "institution": None,
            "course_or_program": None,
            "certificate_id": None,
            "issue_date": None,
            "_raw_model_output": s
        }