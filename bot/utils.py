from datetime import datetime
from zoneinfo import ZoneInfo

from config import TIMEZONE

TZ = ZoneInfo(TIMEZONE)


def now_local() -> datetime:
    return datetime.now(TZ)


def today_local():
    return now_local().date()
