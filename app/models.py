from datetime import date
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, EmailStr, Field, model_validator

PyId = Annotated[str, BeforeValidator(str)]


def serialize(doc: dict) -> dict:
    doc["id"] = str(doc.pop("_id"))
    return doc


class InvestorIn(BaseModel):
    name: str = Field(min_length=1)
    email: str | None = None
    phone: str | None = None
    type_ids: list[str] = Field(default_factory=list)  # investment types this investor is assigned to


class InvestmentTypeIn(BaseModel):
    name: str = Field(min_length=1)
    # Fixed goal. Leave empty or 0 to use the sum of this type's requests instead.
    goal: float | None = Field(default=None, ge=0)
    description: str | None = None


class InvestmentIn(BaseModel):
    investor_id: str
    type_id: str
    amount: float = Field(gt=0)
    date: date
    note: str | None = None


MONTH_PATTERN = r"^\d{4}-(0[1-9]|1[0-2])$"


class RequestIn(BaseModel):
    """A call for funds: each listed investor owes `amount` for the type.

    One-off: due in `start_month`. Recurring: due every month from `start_month`
    through `end_month` (no end date = keeps going).
    """

    type_id: str
    amount: float = Field(gt=0)
    start_month: str = Field(pattern=MONTH_PATTERN)
    recurring: bool = False
    end_month: str | None = Field(default=None, pattern=MONTH_PATTERN)
    investor_ids: list[str] = Field(min_length=1)
    note: str | None = None

    @model_validator(mode="after")
    def check_end(self):
        if not self.recurring:
            self.end_month = None
        elif self.end_month and self.end_month < self.start_month:
            raise ValueError("end_month is before start_month")
        return self


class BulkInvestmentIn(BaseModel):
    """One investment (same type, amount, date) created for each listed investor."""

    investor_ids: list[str] = Field(min_length=1)
    type_id: str
    amount: float = Field(gt=0)
    date: date
    month: str | None = Field(default=None, pattern=MONTH_PATTERN)
    note: str | None = None
    skip_existing: bool = True  # skip investors who already have this type/month/amount


class BulkDeleteIn(BaseModel):
    ids: list[str] = Field(min_length=1)
