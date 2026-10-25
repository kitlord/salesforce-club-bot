from datetime import date
from typing import Optional

import discord

import db
from utils import today_local


class StatusUpdateModal(discord.ui.Modal, title="Daily Status Update"):
    modules_finished = discord.ui.TextInput(
        label="Modules finished (comma-separated numbers)",
        placeholder="e.g. 1, 2, 3",
        style=discord.TextStyle.short,
        max_length=200,
        required=True,
    )
    note = discord.ui.TextInput(
        label="Notes",
        placeholder="What did you learn today?",
        style=discord.TextStyle.paragraph,
        max_length=1000,
        required=False,
    )

    def __init__(self, target_date: Optional[date] = None):
        super().__init__()
        self.target_date = target_date or today_local()

    async def on_submit(self, interaction: discord.Interaction):
        await db.upsert_status_update(
            discord_user_id=interaction.user.id,
            update_date=self.target_date,
            modules_finished=str(self.modules_finished.value).strip(),
            note=str(self.note.value).strip() if self.note.value else None,
        )
        await interaction.response.send_message(
            f"✅ Status update saved for **{self.target_date.isoformat()}**. Thanks!",
            ephemeral=True,
        )


class StatusUpdateReminderView(discord.ui.View):
    def __init__(self, target_date: Optional[date] = None):
        super().__init__(timeout=None)
        self.target_date = target_date

    @discord.ui.button(label="Submit status update", style=discord.ButtonStyle.primary)
    async def submit(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(StatusUpdateModal(self.target_date))
