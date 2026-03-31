import os
import base64
import resend
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

resend.api_key = os.getenv("RESEND_API_KEY")
EMAIL_FROM = os.getenv("EMAIL_FROM", "wedegaertner@gmail.com")


def send_receipt_email(
    to_email: str,
    donor_name: str,
    betrag: str,
    spendendatum: str,
    pdf_bytes: bytes,
) -> dict:
    """Send donation receipt PDF via email using Resend."""
    filename = f"Zuwendungsbestaetigung_{donor_name.replace(' ', '_')}_{spendendatum.replace('.', '')}.pdf"

    params = {
        "from": f"NEA e.V. <{EMAIL_FROM}>",
        "to": [to_email],
        "subject": f"Zuwendungsbestätigung - {donor_name} - {spendendatum}",
        "html": f"""
            <p>Sehr geehrte Damen und Herren,</p>
            <p>anbei erhalten Sie die Zuwendungsbestätigung für Ihre Spende
            in Höhe von {betrag} EUR vom {spendendatum}.</p>
            <p>Vielen Dank für Ihre Unterstützung!</p>
            <p>Mit freundlichen Grüßen,<br>
            Verein "Nachhaltige Entwicklung in Afrika e.V."</p>
        """,
        "attachments": [
            {
                "filename": filename,
                "content": list(pdf_bytes),
            }
        ],
    }

    return resend.Emails.send(params)
