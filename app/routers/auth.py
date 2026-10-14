from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm

from ..db import db
from ..security import CurrentUser, create_token, password_hash

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
async def login(form: Annotated[OAuth2PasswordRequestForm, Depends()]):
    login_id = form.username.strip().lower()
    user = await db.users.find_one({"$or": [{"username": login_id}, {"email": login_id}]})
    if not user or not password_hash.verify(form.password, user["password"]):
        raise HTTPException(401, "Incorrect username or password")
    return {"access_token": create_token(str(user["_id"])), "token_type": "bearer"}


@router.get("/me")
async def me(user: dict = CurrentUser):
    return {"username": user.get("username"), "email": user.get("email")}
