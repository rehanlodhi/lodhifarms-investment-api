from datetime import date
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, EmailStr, Field

PyId = Annotated[str, BeforeValidator(str)]


def serialize(doc: dict) -> dict:
    doc["id"] = str(doc.pop("_id"))
    return doc


class InvestorIn(BaseModel):
    name: str = Field(min_length=1)
    email: str | None = None
    phone: str | None = None


class InvestmentTypeIn(BaseModel):
    name: str = Field(min_length=1)
    goal: float = Field(ge=0)
    description: str | None = None


class InvestmentIn(BaseModel):
    investor_id: str
    type_id: str
    amount: float = Field(gt=0)
    date: date
    note: str | None = None
