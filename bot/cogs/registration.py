import logging
import re

import discord
from discord import app_commands
from discord.ext import commands
from supabase import AuthApiError

import db
from config import DISCORD_GUILD_ID

log = logging.getLogger("status_bot")

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
CODE_RE = re.compile(r"^\d{6}$")


class Registration(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="register", description="Register your email for status update tracking")
    @app_commands.describe(email="Your email address")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def register(self, interaction: discord.Interaction, email: str):
        email = email.strip()
        if not EMAIL_RE.match(email):
            await interaction.response.send_message(
                "That doesn't look like a valid email. Try again, e.g. `/register you@example.com`.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)

        try:
            await db.request_email_otp(email)
        except AuthApiError:
            log.exception("Failed to send OTP to %s", email)
            await interaction.followup.send(
                "Couldn't send a verification email right now (it may be rate-limited). "
                "Please try again in a minute.",
                ephemeral=True,
            )
            return

        await db.upsert_pending_registration(interaction.user.id, email)
        await interaction.followup.send(
            f"📧 Sent a 6-digit verification code to **{email}**. "
            f"Run `/verify <code>` here with that code to finish registering.",
            ephemeral=True,
        )

    @app_commands.command(name="verify", description="Confirm your email with the 6-digit code you were sent")
    @app_commands.describe(code="The 6-digit code from your email")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def verify(self, interaction: discord.Interaction, code: str):
        code = code.strip()
        if not CODE_RE.match(code):
            await interaction.response.send_message(
                "That doesn't look like a 6-digit code. Run `/register <email>` first if you haven't.",
                ephemeral=True,
            )
            return

        pending = await db.get_pending_registration(interaction.user.id)
        if pending is None:
            await interaction.response.send_message(
                "No pending registration found. Run `/register you@example.com` first.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)

        try:
            result = await db.verify_email_otp(pending["email"], code)
        except AuthApiError:
            await interaction.followup.send(
                "That code is invalid or expired. Run `/register` again to get a new one.",
                ephemeral=True,
            )
            return

        if result.user is None:
            await interaction.followup.send(
                "That code is invalid or expired. Run `/register` again to get a new one.",
                ephemeral=True,
            )
            return

        await db.upsert_verified_member(
            discord_user_id=interaction.user.id,
            username=str(interaction.user),
            email=pending["email"],
            guild_id=DISCORD_GUILD_ID,
            auth_user_id=result.user.id,
        )
        await db.delete_pending_registration(interaction.user.id)
        await interaction.followup.send(
            f"✅ Verified **{pending['email']}**. Use `/update` any day to submit your status update.",
            ephemeral=True,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Registration(bot))
