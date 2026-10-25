# Status Update Tracker Bot

Discord bot for the Salesforce Amritapuri server. Tracks each member's daily
status update (modules finished + notes) in Supabase.

## Commands

- `/register <email>` — the bot generates a 6-digit code, stores it (with a 10-minute expiry) in
  Supabase, and emails it via Gmail SMTP — plain text only, no links (DM or any channel).
  Re-running it restarts verification with a new/different email.
- `/verify <code>` — confirms the code from `/register` and marks that Discord account as
  verified in the `members` table (up to `OTP_MAX_ATTEMPTS` wrong guesses before you need a new
  code).
- `/update` — opens a modal (modules finished, notes) and upserts today's update. Works in
  `#status-updates` or DM. Requires `/register` + `/verify` first.
- `/status-update start` — **lead-only.** Turns the daily reminder + missed-update report on.
- `/status-update stop` — **lead-only.** Turns it off.
- `/status-update remove-by-email <email>` — **lead-only.** Permanently deletes the member
  registered with that email and all their status update history (cascades via the DB foreign
  key), plus any pending, unverified registration for that email. Works even if they've already
  left the server (matched by email, not by picking a current Discord member). Case-insensitive,
  irreversible.
- `/status-update test-reminder` — **lead-only.** Runs the 9PM reminder job immediately, regardless
  of on/off state or clock time. For testing.
- `/status-update test-missed` — **lead-only.** Runs the midnight missed-update report
  immediately, regardless of on/off state or clock time. For testing.

## Automated behavior (only while enabled)

- **9:00 PM** (`TIMEZONE`, default `Asia/Kolkata`): DMs every registered member who hasn't
  submitted today's update yet, with a button that opens the update modal directly. If a
  member's DMs are closed, they're pinged in `#status-updates` instead.
- **12:00 AM**: posts in `#status-updates` the list of registered members who missed
  *yesterday's* update. Says nothing if nobody missed.

Same-day updates overwrite the previous entry for that day (no duplicate-row errors) via a
`unique (discord_user_id, update_date)` constraint + upsert.

## One-time setup

### 1. Discord application

1. Create an app at the [Discord Developer Portal](https://discord.com/developers/applications) → **Bot** tab → copy the token into `DISCORD_BOT_TOKEN`.
2. Under **Bot**, enable the **Server Members Intent** (required to DM members and list who's missing).
3. Under **Installation**, enable both **Guild Install** and **User Install** (needed so `/register` and `/update` work in DMs), and set default install scopes to `bot`, `applications.commands`.
4. Generate an OAuth2 invite URL (scopes: `bot`, `applications.commands`; permissions: View Channel, Send Messages, Embed Links) and add the bot to the Salesforce Amritapuri server.
5. In Discord, enable **Developer Mode** (User Settings → Advanced), then right-click the server and `#status-updates` channel to copy `DISCORD_GUILD_ID` and `STATUS_UPDATES_CHANNEL_ID`.
6. Make sure a role named exactly what you set as `LEAD_ROLE_NAME` (default `Lead`) exists and is assigned to your leads.

Note: global slash commands can take up to ~1 hour to show up the first time a command is added or renamed. Subsequent restarts are instant.

### 2. Supabase

Already provisioned in project `cjbgciaiitnnhjvwgggz` (tables: `members`, `status_updates`,
`bot_settings`, `pending_registrations`, all RLS-enabled with no policies — only the
`service_role` key can read/write them, which is what this bot uses). Copy the **service_role**
key (Project Settings → API) into `SUPABASE_SERVICE_ROLE_KEY`. Never put this key in client-side
code.

Email delivery for `/register` does **not** go through Supabase at all — the bot sends the OTP
code itself via Gmail SMTP (see below), as plain text with no link, so there's nothing for an
email provider's link-scanner to consume before the user types in the code.

### 2a. Gmail App Password (for sending OTP codes)

1. Enable **2-Step Verification** on the Google account you want the bot to send from (required
   before Google will let you create an App Password).
2. Go to <https://myaccount.google.com/apppasswords>, create an app password (select "Mail" /
   "Other"), and copy the 16-character password into `GMAIL_APP_PASSWORD`. Put that account's
   address in `GMAIL_ADDRESS`.
3. That's it — no domain verification needed, since you're sending from an address you already
   own. Regular Gmail accounts cap at ~500 recipients/day, far more than this bot needs.

### 3. Run it

```bash
python -m venv .venv
.venv\Scripts\activate         # Windows
pip install -r requirements.txt
copy .env.example .env          # fill in the values
cd bot
python main.py
```

### 4. Deploy (needs to run 24/7)

The 9 PM and 12 AM jobs only fire if the process is running at that moment, so this needs an
always-on host — a small VPS, Railway, Render, Fly.io, or a Raspberry Pi/always-on PC with a
process manager (e.g. `pm2`, `systemd`, or Docker restart policy). A `Dockerfile` is included:

```bash
docker build -t status-bot .
docker run --env-file .env --restart unless-stopped status-bot
```

## Testing

Use a test server (or at least a test channel) so you're not spamming real members — invite the
bot there with its own `DISCORD_GUILD_ID`/`STATUS_UPDATES_CHANNEL_ID`, create a `Lead` role and
give it to yourself.

1. **Run it:** `cd bot && python main.py`. Watch the console for `Logged in as ...` and `Synced N
   global application commands`. First-ever global sync can take up to ~1 hour to show up in
   Discord's command picker — if `/register` doesn't autocomplete yet, that's why; it still works
   once it appears.
2. **Register + verify:** run `/register you@realaddress.com` with an email you can actually
   check. You should get an ephemeral "sent a code" reply and an email from your configured Gmail
   account within a few seconds (plain text, just the code — no link). Run `/verify <code>` with
   those 6 digits. Confirm in Supabase (Table Editor → `members`) that a row appeared with your
   `discord_user_id` and email, and that `pending_registrations` no longer has a row for you.
3. **Update:** run `/update`, fill the modal (e.g. modules `1, 2`, a note), submit. Check
   `status_updates` in Supabase — one row for today. Run `/update` again with different values —
   confirm it's still **one row** (overwritten), not two.
4. **Gating:** try `/update` from a second, unregistered Discord account (or just reason about it)
   — it should refuse and point at `/register`.
5. **Leads check:** without the `Lead` role, run `/status-update start` — expect a permission-denied
   ephemeral reply. Give yourself the role, run it again — expect the "now ON" confirmation, and
   check `bot_settings` in Supabase shows `enabled = true` for your guild.
6. **Reminder job:** with tracking ON, run `/status-update test-reminder`. If you haven't submitted
   today, you should get a DM with a button that opens the same update modal; clicking it and
   submitting should update today's row. If you *did* already submit today, nothing happens to you
   (you're not "missing").
7. **Missed-update job:** run `/status-update test-missed`. Since the bot has no update history
   from "yesterday" in a fresh test, everyone currently registered should show up as having missed
   it — confirming the message posts correctly in `#status-updates` with proper mentions. In real
   production use (after the bot's been running a while), this only lists people actually missing
   the prior day.
8. **Stop:** run `/status-update stop`, then `/status-update test-reminder` again — it still runs
   because `test-*` commands bypass the on/off check by design (that's what makes them useful for
   testing); the *real* 9PM/12AM cron jobs will correctly do nothing while OFF.
9. **Real schedule (optional, slow):** to confirm the actual cron timing works without manually
   triggering, temporarily edit `bot/scheduler.py`'s `CronTrigger(hour=21, minute=0, ...)` to a
   minute or two in the future, restart the bot, wait, confirm it fires, then revert.

## Design notes / assumptions

- "Leads" = anyone holding the `LEAD_ROLE_NAME` Discord role.
- `/register` + `/verify` prove the member actually owns the email (bot-generated OTP, emailed via
  Gmail SMTP, checked against `pending_registrations`) — no roster to validate against, but no
  blind trust either.
- Reminders and the missed-update report only consider members who have `/register`ed; the bot
  has no concept of "everyone in the server," only "everyone who signed up."
- The bot runs for a single guild (`DISCORD_GUILD_ID`).
- If a registered member leaves the server, they're skipped (not purged from Supabase).
