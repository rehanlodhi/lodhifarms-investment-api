from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import settings
from .db import db
from .models import InvestmentTypeIn, InvestorIn
from .routers import auth, investments, stats
from .routers.crud import crud_router
from .security import password_hash


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.jwt_secret in {"change-me", ""}:
        raise RuntimeError("Set a real JWT_SECRET in .env")
    try:
        await db.users.drop_index("email_1")  # replaced by the partial indexes below
    except Exception:
        pass
    only_str = lambda f: {"partialFilterExpression": {f: {"$type": "string"}}}  # noqa: E731
    await db.users.create_index("email", unique=True, name="email_unique", **only_str("email"))
    await db.users.create_index("username", unique=True, name="username_unique", **only_str("username"))

    admin = await db.users.find_one({"$or": [{"username": settings.admin_username}, {"email": settings.admin_email}]})
    if not admin:
        await db.users.insert_one({
            "username": settings.admin_username,
            "email": settings.admin_email,
            "password": password_hash.hash(settings.admin_password),
        })
    elif not admin.get("username"):
        await db.users.update_one({"_id": admin["_id"]}, {"$set": {"username": settings.admin_username}})
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(title="Lodhi Farms Investment", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

api = APIRouter(prefix="/api")
api.include_router(auth.router)
api.include_router(crud_router("/investors", "investors", InvestorIn, "investor_id"))
api.include_router(crud_router("/investment-types", "investment_types", InvestmentTypeIn, "type_id"))
api.include_router(investments.router)
api.include_router(stats.router)
app.include_router(api)

settings.upload_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")
