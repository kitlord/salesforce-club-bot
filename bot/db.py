import asyncio
from datetime import date
from typing import Optional

from supabase import Client, create_client

from config import SUPABASE_SERVICE_ROLE_KEY, SUPABASE_URL

_client: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)


async def _run(fn, *args, **kwargs):
    return await asyncio.to_thread(fn, *args, **kwargs)


def _upsert_verified_member(discord_user_id: int, username: str, email: str, guild_id: int):
    return (
        _client.table("members")
        .upsert(
            {
                "discord_user_id": discord_user_id,
                "discord_username": username,
                "email": email,
                "guild_id": guild_id,
            },
            on_conflict="discord_user_id",
        )
        .execute()
    )


async def upsert_verified_member(discord_user_id: int, username: str, email: str, guild_id: int):
    return await _run(_upsert_verified_member, discord_user_id, username, email, guild_id)


def _get_member_by_email(email: str):
    res = _client.table("members").select("*").ilike("email", email).limit(1).execute()
    return res.data[0] if res.data else None


async def get_member_by_email(email: str) -> Optional[dict]:
    return await _run(_get_member_by_email, email)


def _delete_member_by_email(email: str):
    return _client.table("members").delete().ilike("email", email).execute()


async def delete_member_by_email(email: str):
    return await _run(_delete_member_by_email, email)


def _delete_pending_registration_by_email(email: str):
    return _client.table("pending_registrations").delete().ilike("email", email).execute()


async def delete_pending_registration_by_email(email: str):
    return await _run(_delete_pending_registration_by_email, email)


def _upsert_pending_registration(discord_user_id: int, email: str, code: str, expires_at: str):
    return (
        _client.table("pending_registrations")
        .upsert(
            {
                "discord_user_id": discord_user_id,
                "email": email,
                "code": code,
                "expires_at": expires_at,
                "attempts": 0,
            },
            on_conflict="discord_user_id",
        )
        .execute()
    )


async def upsert_pending_registration(discord_user_id: int, email: str, code: str, expires_at):
    return await _run(_upsert_pending_registration, discord_user_id, email, code, expires_at.isoformat())


def _set_pending_attempts(discord_user_id: int, attempts: int):
    return (
        _client.table("pending_registrations")
        .update({"attempts": attempts})
        .eq("discord_user_id", discord_user_id)
        .execute()
    )


async def set_pending_attempts(discord_user_id: int, attempts: int):
    return await _run(_set_pending_attempts, discord_user_id, attempts)


def _get_pending_registration(discord_user_id: int):
    res = (
        _client.table("pending_registrations")
        .select("*")
        .eq("discord_user_id", discord_user_id)
        .limit(1)
        .execute()
    )
    return res.data[0] if res.data else None


async def get_pending_registration(discord_user_id: int) -> Optional[dict]:
    return await _run(_get_pending_registration, discord_user_id)


def _delete_pending_registration(discord_user_id: int):
    return (
        _client.table("pending_registrations")
        .delete()
        .eq("discord_user_id", discord_user_id)
        .execute()
    )


async def delete_pending_registration(discord_user_id: int):
    return await _run(_delete_pending_registration, discord_user_id)


def _get_member(discord_user_id: int):
    res = (
        _client.table("members")
        .select("*")
        .eq("discord_user_id", discord_user_id)
        .limit(1)
        .execute()
    )
    return res.data[0] if res.data else None


async def get_member(discord_user_id: int) -> Optional[dict]:
    return await _run(_get_member, discord_user_id)


def _list_members(guild_id: int):
    return _client.table("members").select("*").eq("guild_id", guild_id).execute().data


async def list_members(guild_id: int) -> list[dict]:
    return await _run(_list_members, guild_id)


def _upsert_status_update(discord_user_id: int, update_date: str, modules_finished: str, note: Optional[str]):
    return (
        _client.table("status_updates")
        .upsert(
            {
                "discord_user_id": discord_user_id,
                "update_date": update_date,
                "modules_finished": modules_finished,
                "note": note,
            },
            on_conflict="discord_user_id,update_date",
        )
        .execute()
    )


async def upsert_status_update(
    discord_user_id: int, update_date: date, modules_finished: str, note: Optional[str]
):
    return await _run(_upsert_status_update, discord_user_id, update_date.isoformat(), modules_finished, note)


def _submitted_ids_for_date(member_ids: list[int], update_date: str) -> set[int]:
    if not member_ids:
        return set()
    res = (
        _client.table("status_updates")
        .select("discord_user_id")
        .eq("update_date", update_date)
        .in_("discord_user_id", member_ids)
        .execute()
    )
    return {row["discord_user_id"] for row in res.data}


async def list_missing_members(guild_id: int, update_date: date) -> list[dict]:
    members = await _run(_list_members, guild_id)
    member_ids = [m["discord_user_id"] for m in members]
    submitted = await _run(_submitted_ids_for_date, member_ids, update_date.isoformat())
    return [m for m in members if m["discord_user_id"] not in submitted]


def _get_settings(guild_id: int):
    res = _client.table("bot_settings").select("*").eq("guild_id", guild_id).limit(1).execute()
    return res.data[0] if res.data else None


async def is_enabled(guild_id: int) -> bool:
    settings = await _run(_get_settings, guild_id)
    return bool(settings and settings.get("enabled"))


def _set_enabled(guild_id: int, enabled: bool, updated_by: int):
    return (
        _client.table("bot_settings")
        .upsert(
            {"guild_id": guild_id, "enabled": enabled, "updated_by": updated_by},
            on_conflict="guild_id",
        )
        .execute()
    )


async def set_enabled(guild_id: int, enabled: bool, updated_by: int):
    return await _run(_set_enabled, guild_id, enabled, updated_by)
