# Status Update Tracker Bot

Discord bot for the Salesforce Amritapuri server. Tracks each member's daily
status update (modules finished + notes) in Supabase.

## Commands

- `/register <email>` — sends a 6-digit verification code to that email via Supabase Auth (DM or
  any channel). Re-running it restarts verification with a new/different email.
- `/verify <code>` — confirms the code from `/register`, creating a verified Supabase Auth user
  (`auth.users`) linked to your Discord ID.
- `/update` — opens a modal (modules finished, notes) and upserts today's update. Works in
  `#status-updates` or DM. Requires `/register` + `/verify` first.
- `/status-update start` — **lead-only.** Turns the daily reminder + missed-update report on.
- `/status-update stop` — **lead-only.** Turns it off.
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

**One manual dashboard step:** registration uses Supabase Auth's email-OTP sign-in
(`sign_in_with_otp` / `verify_otp`), which by default emails a magic *link*, not a visible code.
Since the user confirms from inside Discord (not a browser), the email needs to show the 6-digit
code instead: go to **Authentication → Email Templates → Magic Link** and make sure the body
includes `{{ .Token }}` (Supabase's default template already has this alongside the link — just
don't remove it). No other Auth config changes are needed.

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
   check. You should get an ephemeral "sent a code" reply and a real email from Supabase within a
   minute or two. Run `/verify <code>` with the 6 digits from that email. Confirm in Supabase
   (Table Editor → `members`) that a row appeared with your `discord_user_id`, email, and a
   non-null `auth_user_id`; check `auth.users` too — it should have a matching confirmed user.
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
- `/register` + `/verify` prove the member actually owns the email (via Supabase Auth OTP) — no
  roster to validate against, but no blind trust either.
- Reminders and the missed-update report only consider members who have `/register`ed; the bot
  has no concept of "everyone in the server," only "everyone who signed up."
- The bot runs for a single guild (`DISCORD_GUILD_ID`).
- If a registered member leaves the server, they're skipped (not purged from Supabase).
