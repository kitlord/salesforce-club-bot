import logging

import discord
from discord import app_commands
from discord.ext import commands

import db
from modals import StatusUpdateModal

log = logging.getLogger("status_bot")


class StatusUpdate(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="update", description="Submit your daily status update")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def update(self, interaction: discord.Interaction):
        member = await db.get_member(interaction.user.id)
        if member is None:
            await interaction.response.send_message(
                "You're not verified yet. Run `/register you@example.com`, then `/verify <code>`.",
                ephemeral=True,
            )
            return
        await interaction.response.send_modal(StatusUpdateModal())


async def setup(bot: commands.Bot):
    await bot.add_cog(StatusUpdate(bot))
