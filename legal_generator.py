from datetime import date


def generate_verification_letter(data: dict) -> str:
    full_name = data.get("full_name") or "[UNKNOWN NAME]"
    institution = data.get("institution") or "[UNKNOWN INSTITUTION]"
    course = data.get("course_or_program") or "[UNKNOWN PROGRAM]"
    cert_id = data.get("certificate_id") or "[UNKNOWN ID]"
    issue_date = data.get("issue_date") or "[UNKNOWN DATE]"

    today = date.today().isoformat()

    return f"""CERTIFICATE VERIFICATION LETTER

Date: {today}

To Whom It May Concern,

This letter is generated to support verification of an academic/professional certificate presented by {full_name}.
Based on the information extracted from the provided certificate document:

- Holder Name: {full_name}
- Institution: {institution}
- Program/Course: {course}
- Certificate ID: {cert_id}
- Issue Date: {issue_date}

This document is generated for verification/administrative use and should be confirmed with the issuing institution where required.

Sincerely,
Automated Document System
"""