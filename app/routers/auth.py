from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm

from ..db import db
from ..security import CurrentUser, create_token, password_hash

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
async def login(form: Annotated[OAuth2PasswordRequestForm, Depends()]):
    user = await db.users.find_one({"email": form.username})
    if not user or not password_hash.verify(form.password, user["password"]):
        raise HTTPException(401, "Incorrect email or password")
    return {"access_token": create_token(user["email"]), "token_type": "bearer"}


@router.get("/me")
async def me(user: dict = CurrentUser):
    return {"email": user["email"]}
