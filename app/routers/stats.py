from fastapi import APIRouter

from ..db import db
from ..security import CurrentUser

router = APIRouter(prefix="/stats", tags=["stats"], dependencies=[CurrentUser])


@router.get("")
async def stats():
    by_type: dict[str, float] = {}
    by_investor: dict[str, float] = {}
    by_month: dict[str, float] = {}
    by_type_month: dict[str, dict[str, float]] = {}
    async for d in db.investments.find():
        by_type[d["type_id"]] = by_type.get(d["type_id"], 0) + d["amount"]
        by_investor[d["investor_id"]] = by_investor.get(d["investor_id"], 0) + d["amount"]
        month = d.get("month") or d["date"][:7]
        by_month[month] = by_month.get(month, 0) + d["amount"]
        tm = by_type_month.setdefault(d["type_id"], {})
        tm[month] = tm.get(month, 0) + d["amount"]

    types = [
        {"id": str(t["_id"]), "name": t["name"], "goal": t["goal"], "raised": by_type.get(str(t["_id"]), 0)}
        async for t in db.investment_types.find().sort("name", 1)
    ]
    investors = [
        {"id": str(i["_id"]), "name": i["name"], "invested": by_investor.get(str(i["_id"]), 0)}
        async for i in db.investors.find().sort("name", 1)
    ]
    return {
        "total_raised": sum(by_type.values()),
        "total_goal": sum(t["goal"] for t in types),
        "types": types,
        "type_months": [{"id": t["id"], "name": t["name"], "months": by_type_month.get(t["id"], {})} for t in types],
        "investors": investors,
        "monthly": [{"month": m, "amount": a} for m, a in sorted(by_month.items())],
    }
