import asyncio
import logging

import discord
from discord.ext import commands

from config import DISCORD_BOT_TOKEN, DISCORD_GUILD_ID, LOG_LEVEL
from scheduler import setup_scheduler

logging.basicConfig(level=LOG_LEVEL, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("status_bot")

INITIAL_COGS = (
    "cogs.registration",
    "cogs.status_update",
    "cogs.admin",
)


class StatusBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)
        self.scheduler = None

    async def setup_hook(self):
        for cog in INITIAL_COGS:
            await self.load_extension(cog)

        synced = await self.tree.sync()
        log.info("Synced %d global application commands", len(synced))

        self.scheduler = setup_scheduler(self)
        self.scheduler.start()
        log.info("Scheduler started")

    async def on_ready(self):
        log.info("Logged in as %s (id=%s), watching guild %s", self.user, self.user.id, DISCORD_GUILD_ID)


async def main():
    bot = StatusBot()
    async with bot:
        await bot.start(DISCORD_BOT_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
