from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from bson import ObjectId
from bson.errors import InvalidId
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pwdlib import PasswordHash

from .config import settings
from .db import db

password_hash = PasswordHash.recommended()
oauth2 = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def create_token(user_id: str) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    return jwt.encode({"sub": user_id, "exp": exp}, settings.jwt_secret, algorithm="HS256")


async def current_user(token: Annotated[str, Depends(oauth2)]) -> dict:
    try:
        user_id = ObjectId(jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])["sub"])
    except (jwt.PyJWTError, InvalidId):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token")
    user = await db.users.find_one({"_id": user_id})
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Unknown user")
    return user


CurrentUser = Depends(current_user)
