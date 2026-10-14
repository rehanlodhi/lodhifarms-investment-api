# Lodhi Farms Investment — API

FastAPI + MongoDB backend (managed with [uv](https://docs.astral.sh/uv/)).

```bash
cp .env.example .env        # set MONGO_URL, JWT_SECRET, ADMIN_PASSWORD
uv sync
uv run uvicorn app.main:app --reload
```

Docs at http://localhost:8000/docs. The admin user from `ADMIN_USERNAME`/`ADMIN_EMAIL`/`ADMIN_PASSWORD` is created on first start.

Manage users:

```bash
uv run python -m app.cli create-user yourname --email you@example.com
uv run python -m app.cli --help
```

Frontend: the `lodhifarms-investment-web` repo.
