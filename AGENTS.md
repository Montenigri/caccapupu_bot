# AGENTS.md

## What this is

Single-file Telegram bot (`caccapupu.py`) that counts 💩 emoji in group chats. Runs via Docker on a VPS.

## Quick start

```bash
pip install -r requirements.txt
# create .env with BOT_TOKEN=...
python caccapupu.py
# or: docker compose up -d --build
```

## Key facts

- **Python 3.12** only supported version
- **No tests** exist — CI only runs `py_compile` + `python -c "import caccapupu"`
- **No linter / formatter** configured — repo has no ruff, black, flake8, etc.
- **python-telegram-bot v21** — all handlers are async (`async def`)
- **DB**: SQLite at `data/emoji_count.db` (configurable via `DB_DIR` env). Auto-created with WAL mode on first run. Never commit `.db` files (in `.gitignore`).
- **`.env`** required with `BOT_TOKEN` — also supports `LOG_LEVEL` (default INFO), `DB_DIR` (default `data/`). Example in `.env.example`.
- **`data/`** dir is volume-mounted in docker-compose and production deploy for DB persistence

## Commands (all Italian)

`/start` `/help` `/lastmonth` `/currentmonth` `/all` `/lasttime`
`/personalstat` `/chart [settimana|mese|anno]` `/streak` `/nostreak`
`/burn` `/ranking [giorno|settimana|mese|anno]` `/monthwinner`

## Milestones

At 100, 500, 1000, 5000 💩 the bot auto-congratulates the user in chat.

## Known issues

- **Command list shows only 1 command**: Telegram clients cache command lists. If only one command appears after typing `/`, force-restart the Telegram app or wait 10 min. The `post_init` now logs success/failure for debugging (`docker logs`).

## Production deploy

CI pushes to VPS via `appleboy/scp-action` + `appleboy/ssh-action`. On deploy it:
1. Recovers the old SQLite DB from the running container before replacing it
2. Builds & runs a Docker container with `--restart unless-stopped`
3. Mounts the host DB directory into `/app/data`

Secrets: `VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY`, `VPS_PORT`, `VPS_APP_DIR`, `VPS_ENV_FILE`, `VPS_DB_DIR`
