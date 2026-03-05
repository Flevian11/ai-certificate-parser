import json
import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "phi3"  # we'll pull this after install


def llm_extract_json(raw_text: str) -> dict:
    """
    Sends certificate text to Ollama and returns extracted fields as JSON dict.
    """
    prompt = f"""
You are an information extraction system.
Extract these fields from the certificate text, return VALID JSON ONLY:

- full_name
- institution
- course_or_program
- certificate_id
- issue_date

Rules:
- If missing, use null.
- issue_date should be ISO format YYYY-MM-DD if possible, else null.
- Output JSON only, no explanations.

CERTIFICATE TEXT:
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