import logging
from datetime import timedelta

import discord
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

import db
from config import DISCORD_GUILD_ID, STATUS_UPDATES_CHANNEL_ID, TIMEZONE
from modals import StatusUpdateReminderView
from utils import today_local

log = logging.getLogger("status_bot")


def setup_scheduler(bot: discord.Client) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=TIMEZONE)
    scheduler.add_job(
        send_reminders, CronTrigger(hour=21, minute=0, timezone=TIMEZONE), args=[bot], id="send_reminders"
    )
    scheduler.add_job(
        post_missed_updates,
        CronTrigger(hour=0, minute=0, timezone=TIMEZONE),
        args=[bot],
        id="post_missed_updates",
    )
    return scheduler


async def send_reminders(bot: discord.Client, force: bool = False):
    if not force and not await db.is_enabled(DISCORD_GUILD_ID):
        return

    guild = bot.get_guild(DISCORD_GUILD_ID)
    if guild is None:
        log.warning("Guild %s not found for reminder job", DISCORD_GUILD_ID)
        return

    today = today_local()
    missing = await db.list_missing_members(DISCORD_GUILD_ID, today)
    unreachable = []

    for row in missing:
        member = guild.get_member(row["discord_user_id"])
        if member is None:
            continue
        try:
            await member.send(
                f"👋 Reminder: you haven't submitted your status update for **{today.isoformat()}** yet.",
                view=StatusUpdateReminderView(today),
            )
        except discord.Forbidden:
            unreachable.append(member)
        except discord.HTTPException:
            log.exception("Failed to DM member %s", member.id)
            unreachable.append(member)

    if unreachable:
        channel = guild.get_channel(STATUS_UPDATES_CHANNEL_ID)
        if channel is not None:
            mentions = " ".join(m.mention for m in unreachable)
            await channel.send(
                f"⏰ Reminder: {mentions} — please submit today's status update with `/update` "
                "(your DMs are closed, so I couldn't reach you there)."
            )


async def post_missed_updates(bot: discord.Client, force: bool = False):
    if not force and not await db.is_enabled(DISCORD_GUILD_ID):
        return

    guild = bot.get_guild(DISCORD_GUILD_ID)
    if guild is None:
        log.warning("Guild %s not found for missed-updates job", DISCORD_GUILD_ID)
        return

    target_date = today_local() - timedelta(days=1)
    missing = await db.list_missing_members(DISCORD_GUILD_ID, target_date)
    if not missing:
        return

    channel = guild.get_channel(STATUS_UPDATES_CHANNEL_ID)
    if channel is None:
        log.warning("Status updates channel %s not found", STATUS_UPDATES_CHANNEL_ID)
        return

    lines = []
    for row in missing:
        member = guild.get_member(row["discord_user_id"])
        lines.append(f"- {member.mention if member else row['discord_username']}")

    await channel.send(f"🚨 **Missed status updates for {target_date.isoformat()}:**\n" + "\n".join(lines))
