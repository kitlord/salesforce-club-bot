import logging

import discord
from discord import app_commands
from discord.ext import commands

import db
import scheduler
from config import LEAD_ROLE_NAME

log = logging.getLogger("status_bot")


def is_lead(interaction: discord.Interaction) -> bool:
    if interaction.guild is None or not isinstance(interaction.user, discord.Member):
        return False
    return any(role.name.lower() == LEAD_ROLE_NAME.lower() for role in interaction.user.roles)


class Admin(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    status_update_group = app_commands.Group(
        name="status-update", description="Control the daily status update tracker"
    )

    @status_update_group.command(name="start", description="Enable daily status update tracking for this server")
    @app_commands.check(is_lead)
    async def start(self, interaction: discord.Interaction):
        await db.set_enabled(interaction.guild.id, True, interaction.user.id)
        await interaction.response.send_message(
            "✅ Status update tracking is now **ON**. Members get a DM reminder at 9 PM if they haven't "
            "submitted, and missed updates are posted here just after midnight."
        )

    @status_update_group.command(name="stop", description="Disable daily status update tracking for this server")
    @app_commands.check(is_lead)
    async def stop(self, interaction: discord.Interaction):
        await db.set_enabled(interaction.guild.id, False, interaction.user.id)
        await interaction.response.send_message("🛑 Status update tracking is now **OFF**.")

    @status_update_group.command(
        name="test-reminder", description="Manually run tonight's 9PM reminder job right now (testing)"
    )
    @app_commands.check(is_lead)
    async def test_reminder(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        await scheduler.send_reminders(self.bot, force=True)
        await interaction.followup.send(
            "Ran the reminder job. Anyone missing today's update should have gotten a DM "
            "(or a mention here if their DMs are closed).",
            ephemeral=True,
        )

    @status_update_group.command(
        name="test-missed", description="Manually run the missed-updates report right now (testing)"
    )
    @app_commands.check(is_lead)
    async def test_missed(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        await scheduler.post_missed_updates(self.bot, force=True)
        await interaction.followup.send(
            "Ran the missed-updates job. If anyone was missing *yesterday's* update, it was posted "
            "in this channel (nothing is posted if nobody missed).",
            ephemeral=True,
        )

    @start.error
    @stop.error
    @test_reminder.error
    @test_missed.error
    async def on_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CheckFailure):
            await interaction.response.send_message(
                f"Only members with the **{LEAD_ROLE_NAME}** role can do that.", ephemeral=True
            )
        else:
            log.exception("Admin command error", exc_info=error)
            if not interaction.response.is_done():
                await interaction.response.send_message("Something went wrong.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Admin(bot))
