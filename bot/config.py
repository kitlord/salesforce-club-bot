import os

from dotenv import load_dotenv

load_dotenv()


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


DISCORD_BOT_TOKEN = _require("DISCORD_BOT_TOKEN")
DISCORD_GUILD_ID = int(_require("DISCORD_GUILD_ID"))
STATUS_UPDATES_CHANNEL_ID = int(_require("STATUS_UPDATES_CHANNEL_ID"))
LEAD_ROLE_NAME = os.environ.get("LEAD_ROLE_NAME", "Lead")

SUPABASE_URL = _require("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = _require("SUPABASE_SERVICE_ROLE_KEY")

GMAIL_ADDRESS = _require("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = _require("GMAIL_APP_PASSWORD")
GMAIL_SENDER_NAME = os.environ.get("GMAIL_SENDER_NAME", "Salesforce Amritapuri Status Bot")

OTP_TTL_MINUTES = int(os.environ.get("OTP_TTL_MINUTES", "10"))
OTP_MAX_ATTEMPTS = int(os.environ.get("OTP_MAX_ATTEMPTS", "5"))

TIMEZONE = os.environ.get("TIMEZONE", "Asia/Kolkata")
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
