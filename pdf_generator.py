from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from datetime import datetime, timedelta


def _safe(v):
    return "" if v is None else str(v).strip()


def _fmt_date(dt: datetime) -> str:
    return dt.strftime("%d-%m-%Y")


def _draw_background(c: canvas.Canvas, w: float, h: float):
    # Paper base
    c.setFillColor(colors.HexColor("#F7FAFF"))
    c.rect(0, 0, w, h, stroke=0, fill=1)

    # Top band tint
    c.setFillColor(colors.HexColor("#EEF2FF"))
    c.rect(0, h - 52 * mm, w, 52 * mm, stroke=0, fill=1)

    # Subtle watermark text (official look)
    c.saveState()
    c.setFillColor(colors.Color(0.02, 0.08, 0.22, alpha=0.05))
    c.setFont("Helvetica-Bold", 58)
    c.translate(w / 2, h / 2)
    c.rotate(25)
    c.drawCentredString(0, 0, "VERIFIED")
    c.restoreState()


def _wrap(c: canvas.Canvas, text: str, x: float, y: float, max_w: float, font="Helvetica", size=10, leading=14):
    c.setFont(font, size)
    words = (text or "").split()
    line = ""
    for word in words:
        test = (line + " " + word).strip()
        if c.stringWidth(test, font, size) <= max_w:
            line = test
        else:
            c.drawString(x, y, line)
            y -= leading
            line = word
    if line:
        c.drawString(x, y, line)
        y -= leading
    return y


def generate_verification_pdf(data: dict, letter_text: str, output_path: str) -> None:
    c = canvas.Canvas(output_path, pagesize=A4)
    w, h = A4

    _draw_background(c, w, h)

    margin = 14 * mm
    inner = margin + 6 * mm

    # Borders
    c.setStrokeColor(colors.HexColor("#0F172A"))
    c.setLineWidth(1)
    c.rect(margin, margin, w - 2 * margin, h - 2 * margin, stroke=1, fill=0)

    c.setStrokeColor(colors.HexColor("#CBD5E1"))
    c.setLineWidth(1)
    c.rect(inner, inner, w - 2 * inner, h - 2 * inner, stroke=1, fill=0)

    # Core fields
    issuing_body = _safe(data.get("issuing_body") or "AI CERTIFICATE PARSER")
    doc_title = _safe(data.get("document_title") or "Verification Certificate")

    # Use SYSTEM serial, not OCR serial
    system_ref = _safe(data.get("system_ref") or "ACP-" + datetime.now().strftime("%Y%m%d") + "-XXXXXX")

    full_name = _safe(data.get("full_name"))
    national_id = _safe(data.get("national_id"))
    status_statement = _safe(data.get("status_statement") or "Status could not be reliably extracted from the document text.")

    # Dates (fallback)
    issue_date_str = _safe(data.get("issue_date"))
    valid_until_str = _safe(data.get("valid_until"))
    if not issue_date_str:
        issue_dt = datetime.now()
        issue_date_str = _fmt_date(issue_dt)
    else:
        # keep as string
        issue_dt = datetime.now()

    if not valid_until_str:
        valid_until_str = _fmt_date(datetime.now() + timedelta(days=365))

    # ===== Header: serial (top-right) =====
    c.setFillColor(colors.HexColor("#0F172A"))
    c.setFont("Helvetica", 10)
    c.drawRightString(w - inner, h - inner - 4 * mm, f"Verification Ref: {system_ref}")

    # ===== Issuer + Title =====
    y = h - inner - 20 * mm
    c.setFont("Helvetica-Bold", 22)
    c.drawCentredString(w / 2, y, issuing_body)

    y -= 14 * mm
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(w / 2, y, doc_title)

    y -= 9 * mm
    c.setFont("Helvetica", 11)
    c.setFillColor(colors.HexColor("#334155"))
    c.drawCentredString(w / 2, y, "This is to certify that:")

    # ===== Subject (center) =====
    y -= 14 * mm
    c.setFillColor(colors.HexColor("#0F172A"))
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(w / 2, y, full_name if full_name else "—")

    y -= 9 * mm
    c.setFont("Helvetica", 11)
    if national_id:
        c.drawCentredString(w / 2, y, f"Holder of National ID No. {national_id}")
        y -= 9 * mm

    # ===== Status statement (centered, concise) =====
    c.setFont("Helvetica", 11)
    c.setFillColor(colors.HexColor("#0F172A"))
    c.drawCentredString(w / 2, y, status_statement[:120] if status_statement else "—")

    # ===== Details block (clean + logical) =====
    y -= 18 * mm
    box_x = inner + 6 * mm
    box_w = w - 2 * inner - 12 * mm
    box_h = 44 * mm

    c.setFillColor(colors.white)
    c.setStrokeColor(colors.HexColor("#E2E8F0"))
    c.roundRect(box_x, y - box_h + 8 * mm, box_w, box_h, 8, stroke=1, fill=1)

    c.setFillColor(colors.HexColor("#0F172A"))
    c.setFont("Helvetica-Bold", 11)
    c.drawString(box_x + 10, y + 2 * mm, "Verification Summary")

    c.setFont("Helvetica", 9.5)
    c.setFillColor(colors.HexColor("#334155"))

    # two-column fields
    left_x = box_x + 10
    right_x = box_x + box_w / 2 + 10
    row_y = y - 8 * mm
    gap = 6 * mm

    def row(x, yy, label, value):
        c.setFont("Helvetica-Bold", 9)
        c.drawString(x, yy, f"{label}:")
        c.setFont("Helvetica", 9)
        c.drawString(x + 28 * mm, yy, value if value else "—")

    row(left_x, row_y, "Name", full_name)
    row(right_x, row_y, "National ID", national_id)

    row_y -= gap
    row(left_x, row_y, "Issue Date", issue_date_str)
    row(right_x, row_y, "Valid Until", valid_until_str)

    row_y -= gap
    row(left_x, row_y, "Reference", system_ref)
    row(right_x, row_y, "Confidence", f"{round(float(data.get('confidence', 0.0))*100,1)}%" if isinstance(data.get("confidence"), (int, float)) else "—")

    # ===== Caveat =====
    cave_y = margin + 56 * mm
    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(colors.HexColor("#0F172A"))
    c.drawString(inner, cave_y + 22, "Caveat")

    c.setFont("Helvetica", 9)
    c.setFillColor(colors.HexColor("#334155"))
    max_w = w - 2 * inner

    y_c = cave_y + 10
    y_c = _wrap(c, "a) This document is system-generated from OCR + local AI. It reflects only what was readable from the submitted file.",
                inner, y_c, max_w, size=9, leading=12)
    _wrap(c, "b) For high-stakes decisions, verify using the issuer’s official verification channels.",
          inner, y_c, max_w, size=9, leading=12)

    # ===== Officer block (typed names + titles) =====
    # NOTE: No forged signatures. Use signature lines only.
    sig_line_y = margin + 82 * mm
    c.setStrokeColor(colors.HexColor("#111827"))
    c.setLineWidth(1)

    # left sign line
    c.line(inner + 8 * mm, sig_line_y, inner + 78 * mm, sig_line_y)
    # right sign line
    c.line(w - inner - 78 * mm, sig_line_y, w - inner - 8 * mm, sig_line_y)

    # officer names & roles (you can edit names safely as typed)
    ceo_name = _safe(data.get("system_ceo") or "Flevian Ahithopel")
    coo_name = _safe(data.get("system_coo") or "Yasmin Aaliyah")

    c.setFillColor(colors.HexColor("#0F172A"))
    c.setFont("Helvetica-Bold", 9.5)
    c.drawString(inner + 8 * mm, sig_line_y - 12, ceo_name)
    c.drawRightString(w - inner - 8 * mm, sig_line_y - 12, coo_name)

    c.setFont("Helvetica", 9)
    c.setFillColor(colors.HexColor("#334155"))
    c.drawString(inner + 8 * mm, sig_line_y - 24, "Chief Executive Officer (System)")
    c.drawRightString(w - inner - 8 * mm, sig_line_y - 24, "Chief Operations Officer (System)")

    # ===== Footer dates =====
    c.setFont("Helvetica", 10)
    c.setFillColor(colors.HexColor("#0F172A"))
    c.drawString(inner, margin + 14 * mm, f"Date of Issue: {issue_date_str}")
    c.drawRightString(w - inner, margin + 14 * mm, f"Valid until: {valid_until_str}")

    c.showPage()
    c.save()