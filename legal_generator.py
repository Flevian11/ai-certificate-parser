from datetime import datetime


def _g(d, key, default=""):
    v = d.get(key, default)
    if v is None:
        return ""
    return str(v).strip()


def generate_verification_letter(extracted: dict) -> str:
    """
    Produces a professional verification letter from extracted fields.
    Never invents missing fields: if a key is missing, it is omitted or marked as 'Not provided'.
    """

    issuing_body = _g(extracted, "issuing_body") or "Verification Authority"
    doc_title = _g(extracted, "document_title") or "Verification Document"

    full_name = _g(extracted, "full_name")
    national_id = _g(extracted, "national_id")
    cert_no = _g(extracted, "certificate_number")

    institution = _g(extracted, "institution")
    degree = _g(extracted, "degree_or_certificate")
    program = _g(extracted, "course_or_program")
    issue_date = _g(extracted, "issue_date")
    valid_until = _g(extracted, "valid_until")

    status_statement = _g(extracted, "status_statement")

    website = _g(extracted, "website")
    contact_email = _g(extracted, "contact_email")
    contact_phone = _g(extracted, "contact_phone")

    confidence = extracted.get("confidence", None)
    missing_fields = extracted.get("missing_fields", [])

    generated_at = datetime.now().strftime("%d-%m-%Y %H:%M")

    # Build a clean letter
    lines = []
    lines.append(f"{issuing_body}")
    lines.append(f"{doc_title}")
    lines.append("")
    lines.append("To Whom It May Concern,")
    lines.append("")
    lines.append("RE: CERTIFICATE / DOCUMENT VERIFICATION")

    # Identity block (only include what we have)
    lines.append("")
    lines.append("This letter is generated based on the text extracted from the submitted document.")
    lines.append("The following details were identified:")

    def add_field(label, value):
        if value:
            lines.append(f"- {label}: {value}")
        else:
            lines.append(f"- {label}: Not provided")

    add_field("Full Name", full_name)
    add_field("National ID", national_id)
    add_field("Certificate / Serial Number", cert_no)
    add_field("Institution", institution)
    add_field("Degree / Certificate", degree)
    add_field("Course / Program", program)
    add_field("Issue Date", issue_date)
    add_field("Valid Until", valid_until)

    if status_statement:
        lines.append("")
        lines.append(f"Status: {status_statement}")

    # Notes on quality (industry-grade transparency)
    lines.append("")
    lines.append("Verification Notes:")
    lines.append("- This output is system-generated (OCR + local language model).")
    lines.append("- If any field is shown as 'Not provided', it was not reliably present in the document text.")
    lines.append("- For high-stakes decisions, confirm using the issuer’s official channels where available.")

    if website or contact_email or contact_phone:
        lines.append("")
        lines.append("Issuer Contact (if present in document):")
        if website:
            lines.append(f"- Website: {website}")
        if contact_email:
            lines.append(f"- Email: {contact_email}")
        if contact_phone:
            lines.append(f"- Phone: {contact_phone}")

    # Optional confidence summary
    if isinstance(confidence, (int, float)):
        lines.append("")
        lines.append(f"Extraction Confidence: {round(float(confidence) * 100, 1)}%")

    if isinstance(missing_fields, list) and missing_fields:
        lines.append(f"Missing Fields: {', '.join(missing_fields[:20])}")

    lines.append("")
    lines.append(f"Generated: {generated_at}")
    lines.append("")
    lines.append("Sincerely,")
    lines.append("AI Certificate Parser System")
    lines.append("(Local OCR + Local LLM)")

    return "\n".join(lines)