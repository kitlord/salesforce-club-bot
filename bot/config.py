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

TIMEZONE = os.environ.get("TIMEZONE", "Asia/Kolkata")
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
