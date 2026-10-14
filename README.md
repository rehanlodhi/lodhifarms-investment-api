# Lodhi Farms Investment — API

FastAPI + MongoDB backend (managed with [uv](https://docs.astral.sh/uv/)).

```bash
cp .env.example .env        # set MONGO_URL, JWT_SECRET, ADMIN_PASSWORD
uv sync
uv run uvicorn app.main:app --reload
```

Docs at http://localhost:8000/docs. The admin user from `ADMIN_USERNAME`/`ADMIN_EMAIL`/`ADMIN_PASSWORD` is created on first start.

## Users

Run these from the `api` folder. They use the `MONGO_URL` in `.env`, so on the server they change the live database.

```bash
uv run python -m app.cli create-user yourname --email you@example.com   # prompts for the password; email is optional
uv run python -m app.cli list-users
uv run python -m app.cli set-password yourname
uv run python -m app.cli delete-user yourname
uv run python -m app.cli --help
```

A user can log in with either the username or the email. Avoid `--password`: it ends up in your shell history, so let it prompt.

## Sync production data to local

`scripts/sync_prod_to_local.py` copies investors, types, investments and requests from the production database (Atlas) into your local one. Production is only read. It is a local helper and is not committed to this repo (it is listed in `.git/info/exclude`).

Setup, once: put the Atlas connection string in `api/.env.prod`, which must stay out of git:

```
PROD_MONGO_URL=mongodb+srv://<user>:<password>@<cluster>.mongodb.net
```

```bash
uv run python scripts/sync_prod_to_local.py            # dry run: shows what would change, writes nothing
uv run python scripts/sync_prod_to_local.py --apply    # replace local data with prod data
```

- `MONGO_URL` in `.env` must be your local Mongo. The script refuses to run if it points at Atlas or any remote host.
- Local data is saved to `.backups/` before it is replaced, and restored if the copy fails.
- The `users` collection and screenshot files are not copied.

Frontend: the `lodhifarms-investment-web` repo.
