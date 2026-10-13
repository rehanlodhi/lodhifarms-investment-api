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
    await db.users.create_index("email", unique=True)
    if not await db.users.find_one({"email": settings.admin_email}):
        await db.users.insert_one(
            {"email": settings.admin_email, "password": password_hash.hash(settings.admin_password)}
        )
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
