import logging
import re
import secrets
from datetime import datetime, timedelta

import discord
from discord import app_commands
from discord.ext import commands

import db
from config import DISCORD_GUILD_ID, OTP_MAX_ATTEMPTS, OTP_TTL_MINUTES
from email_sender import send_otp_email
from utils import now_local

log = logging.getLogger("status_bot")

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
CODE_RE = re.compile(r"^\d{6}$")


def _generate_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


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

        code = _generate_code()
        expires_at = now_local() + timedelta(minutes=OTP_TTL_MINUTES)

        try:
            await send_otp_email(email, code)
        except Exception:
            log.exception("Failed to send OTP email to %s", email)
            await interaction.followup.send(
                "Couldn't send the verification email right now. Please try again shortly.",
                ephemeral=True,
            )
            return

        await db.upsert_pending_registration(interaction.user.id, email, code, expires_at)
        await interaction.followup.send(
            f"📧 Sent a 6-digit verification code to **{email}** (expires in {OTP_TTL_MINUTES} minutes). "
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

        if now_local() > datetime.fromisoformat(pending["expires_at"]):
            await db.delete_pending_registration(interaction.user.id)
            await interaction.response.send_message(
                "That code expired. Run `/register` again to get a new one.", ephemeral=True
            )
            return

        if pending["attempts"] >= OTP_MAX_ATTEMPTS:
            await db.delete_pending_registration(interaction.user.id)
            await interaction.response.send_message(
                "Too many incorrect attempts. Run `/register` again to get a new code.", ephemeral=True
            )
            return

        if not secrets.compare_digest(code, pending["code"]):
            attempts = pending["attempts"] + 1
            await db.set_pending_attempts(interaction.user.id, attempts)
            remaining = OTP_MAX_ATTEMPTS - attempts
            await interaction.response.send_message(
                f"That code is incorrect. {remaining} attempt(s) left.", ephemeral=True
            )
            return

        await db.upsert_verified_member(
            discord_user_id=interaction.user.id,
            username=str(interaction.user),
            email=pending["email"],
            guild_id=DISCORD_GUILD_ID,
        )
        await db.delete_pending_registration(interaction.user.id)
        await interaction.response.send_message(
            f"✅ Verified **{pending['email']}**. Use `/update` any day to submit your status update.",
            ephemeral=True,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Registration(bot))
