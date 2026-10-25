import asyncio
import smtplib
import ssl
from email.message import EmailMessage

from config import GMAIL_ADDRESS, GMAIL_APP_PASSWORD, GMAIL_SENDER_NAME, OTP_TTL_MINUTES

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587


def _send_otp_email(to_email: str, code: str):
    msg = EmailMessage()
    msg["Subject"] = "Your status update bot verification code"
    msg["From"] = f"{GMAIL_SENDER_NAME} <{GMAIL_ADDRESS}>"
    msg["To"] = to_email
    msg.set_content(
        f"Your verification code is: {code}\n\n"
        f"Enter it in Discord with /verify {code}\n\n"
        f"This code expires in {OTP_TTL_MINUTES} minutes and can only be used once."
    )

    context = ssl.create_default_context()
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls(context=context)
        server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        server.send_message(msg)


async def send_otp_email(to_email: str, code: str):
    await asyncio.to_thread(_send_otp_email, to_email, code)
