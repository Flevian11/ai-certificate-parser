import json
import re
import requests
from typing import Any, Dict, Optional

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "phi3:latest"

# Keep output consistent for PDF + legal doc
TARGET_FIELDS = [
    "issuing_body",
    "document_title",
    "certificate_number",
    "full_name",
    "national_id",
    "institution",
    "degree_or_certificate",
    "course_or_program",
    "issue_date",
    "valid_until",
    "status_statement",
    "contact_email",
    "contact_phone",
    "website",
]


def _strip_code_fences(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r"^```(?:json)?\s*", "", s, flags=re.IGNORECASE)
    s = re.sub(r"\s*```$", "", s)
    return s.strip()


def _try_parse_json(text: str) -> Optional[Dict[str, Any]]:
    text = _strip_code_fences(text)

    # direct JSON
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass

    # extract first {...} block
    m = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if m:
        blob = m.group(0)
        try:
            obj = json.loads(blob)
            if isinstance(obj, dict):
                return obj
        except Exception:
            return None
    return None


def _normalize(d: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}

    for k, v in (d or {}).items():
        key = str(k).strip()
        if isinstance(v, str):
            vv = v.strip()
            if vv.lower() in {"n/a", "na", "none", "null", "unknown", "-"}:
                vv = ""
            out[key] = vv
        else:
            out[key] = v

    # common aliases
    aliases = {
        "name": "full_name",
        "id_no": "national_id",
        "id_number": "national_id",
        "serial_no": "certificate_number",
        "certificate_serial": "certificate_number",
        "valid_till": "valid_until",
        "valid_to": "valid_until",
        "issuer": "issuing_body",
        "title": "document_title",
        "program": "course_or_program",
        "course": "course_or_program",
        "qualification": "degree_or_certificate",
        "degree": "degree_or_certificate",
        "email": "contact_email",
        "phone": "contact_phone",
    }

    for src, dst in aliases.items():
        if dst not in out and src in out and isinstance(out[src], str) and out[src].strip():
            out[dst] = out[src].strip()

    # build final dict with fixed keys
    final: Dict[str, Any] = {f: "" for f in TARGET_FIELDS}
    for f in TARGET_FIELDS:
        val = out.get(f, "")
        final[f] = val.strip() if isinstance(val, str) else val

    # quality fields (optional)
    conf = out.get("confidence")
    if isinstance(conf, (int, float)):
        final["confidence"] = max(0.0, min(1.0, float(conf)))

    missing = out.get("missing_fields")
    if isinstance(missing, list):
        final["missing_fields"] = [str(x) for x in missing][:50]
    else:
        final["missing_fields"] = [k for k in TARGET_FIELDS if not str(final.get(k, "")).strip()]

    notes = out.get("notes")
    if isinstance(notes, str) and notes.strip():
        final["notes"] = notes.strip()

    return final


def _fallback_extract(text: str) -> Dict[str, Any]:
    """
    Regex fallback to return whatever is available without guessing.
    """
    t = text or ""

    def find(patterns):
        for p in patterns:
            m = re.search(p, t, flags=re.IGNORECASE)
            if m:
                return m.group(1).strip()
        return ""

    cert_no = find([
        r"Certificate\s*Serial\s*No\.?\s*[:\-]?\s*([A-Z0-9\/\-]+)",
        r"Serial\s*No\.?\s*[:\-]?\s*([A-Z0-9\/\-]+)",
        r"Ref\.?\s*No\.?\s*[:\-]?\s*([A-Z0-9\/\-]+)",
    ])

    national_id = find([
        r"National\s*ID\s*(?:NO\.?|No\.?)\s*[:\-]?\s*([0-9A-Z\-\/]+)",
        r"ID\s*(?:NO\.?|No\.?)\s*[:\-]?\s*([0-9A-Z\-\/]+)",
    ])

    # issuer from early lines (best long uppercase-ish line)
    lines = [ln.strip() for ln in t.splitlines() if ln.strip()]
    head = lines[:8]
    issuing_body = ""
    for ln in head:
        if len(ln) >= 12 and sum(ch.isalpha() for ch in ln) >= 8:
            issuing_body = ln[:80]
            break

    title = find([
        r"\b(Compliance\s+Certificate)\b",
        r"\b(Verification\s+Certificate)\b",
        r"\b(Recognition\s+Letter)\b",
        r"\b(Certificate)\b",
    ])

    full_name = find([
        r"confirm\s+that;?\s*\n\s*([A-Z][A-Z\s]{4,60})",
        r"confirm\s+that;?\s*([A-Z][A-Z\s]{4,60})",
        r"\bName\s*[:\-]?\s*([A-Z][A-Za-z\s]{3,80})",
    ])

    issue_date = find([
        r"Date\s+of\s+Issue\s*[:\-]?\s*([0-9]{1,2}[-\/][0-9]{1,2}[-\/][0-9]{2,4})",
        r"Issued\s+on\s*[:\-]?\s*([0-9]{1,2}[-\/][0-9]{1,2}[-\/][0-9]{2,4})",
    ])

    valid_until = find([
        r"Valid\s+until\s*[:\-]?\s*([0-9]{1,2}[-\/][0-9]{1,2}[-\/][0-9]{2,4})",
        r"Valid\s+till\s*[:\-]?\s*([0-9]{1,2}[-\/][0-9]{1,2}[-\/][0-9]{2,4})",
    ])

    status_statement = find([
        r"is\s+(not\s+a\s+beneficiary[^\.]{0,140}\.)",
        r"is\s+(a\s+beneficiary[^\.]{0,140}\.)",
    ])

    # optional contact bits
    email = find([r"([A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,})"])
    website = find([r"\b((?:https?:\/\/)?(?:www\.)?[a-z0-9.-]+\.[a-z]{2,})\b"])

    out = {f: "" for f in TARGET_FIELDS}
    out.update({
        "issuing_body": issuing_body,
        "document_title": title,
        "certificate_number": cert_no,
        "full_name": full_name,
        "national_id": national_id,
        "issue_date": issue_date,
        "valid_until": valid_until,
        "status_statement": status_statement,
        "contact_email": email,
        "website": website,
        "confidence": 0.35,
        "notes": "Fallback regex extraction used for some fields.",
    })

    out["missing_fields"] = [k for k in TARGET_FIELDS if not str(out.get(k, "")).strip()]
    return _normalize(out)


def llm_extract_json(raw_text: str) -> Dict[str, Any]:
    """
    Calls Ollama and returns best-effort extracted fields.
    - Never guesses / fabricates
    - Returns partial fields when available
    - Falls back to regex extraction if LLM fails or output isn't valid JSON
    """
    text = (raw_text or "").strip()
    if not text:
        return {"_llm_error": "Empty OCR text", "confidence": 0.0, "missing_fields": TARGET_FIELDS[:]}

    prompt = f"""
You are an information extraction system.
Extract ONLY what is explicitly present in the text.
Do NOT guess. Do NOT invent names, IDs, dates, or numbers.
If a field is not present or not reliable, return an empty string "" for that field.

Return STRICT JSON ONLY (no markdown, no explanation).
Keys must match exactly these fields:
{", ".join(TARGET_FIELDS)}

Also include:
- confidence: number 0..1 (how complete & clear the extracted info is)
- missing_fields: list of keys that are empty

Text:
<<<
{text[:12000]}
>>>
""".strip()

    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.1,
            "num_predict": 650,
        },
    }

    try:
        r = requests.post(OLLAMA_URL, json=payload, timeout=150)
        r.raise_for_status()
        resp = (r.json().get("response") or "").strip()
    except Exception as e:
        out = _fallback_extract(text)
        out["_llm_error"] = f"Ollama call failed: {e}"
        return out

    parsed = _try_parse_json(resp)
    if not parsed:
        out = _fallback_extract(text)
        out["_llm_error"] = "LLM output was not valid JSON; fallback extraction used."
        return out

    # ensure missing/confidence exist
    if "missing_fields" not in parsed:
        parsed["missing_fields"] = [k for k in TARGET_FIELDS if not str(parsed.get(k, "")).strip()]

    if "confidence" not in parsed:
        filled = sum(1 for k in TARGET_FIELDS if str(parsed.get(k, "")).strip())
        parsed["confidence"] = round(min(0.95, 0.25 + (filled / max(1, len(TARGET_FIELDS))) * 0.7), 2)

    return _normalize(parsed)