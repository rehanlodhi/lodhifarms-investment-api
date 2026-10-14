from datetime import datetime, timedelta, timezone

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

    requested = await owed_by_type()  # sum of requests due so far, per type
    types = [
        {
            "id": str(t["_id"]),
            "name": t["name"],
            # A goal of 0/null means "no fixed goal": use the sum of the type's requests.
            "goal": t.get("goal") or requested.get(str(t["_id"]), 0),
            "raised": by_type.get(str(t["_id"]), 0),
        }
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


# "Current month" for dues is taken in Pakistan time (UTC+5).
PKT = timezone(timedelta(hours=5))


def month_index(month: str) -> int:
    year, mo = month.split("-")
    return int(year) * 12 + int(mo) - 1


def months_due(req: dict, current: int) -> int:
    """How many monthly instalments of this request are due up to `current`."""
    start = month_index(req["start_month"])
    if not req.get("recurring"):
        return 1 if start <= current else 0
    end = min(month_index(req["end_month"]), current) if req.get("end_month") else current
    return max(0, end - start + 1)


async def owed_by_type(current: int | None = None) -> dict[str, float]:
    """Total owed per type through the current month (every investor in every request)."""
    if current is None:
        now = datetime.now(PKT)
        current = month_index(f"{now.year}-{now.month:02d}")
    totals: dict[str, float] = {}
    async for r in db.requests.find():
        totals[r["type_id"]] = totals.get(r["type_id"], 0) + months_due(r, current) * r["amount"] * len(r["investor_ids"])
    return totals


@router.get("/investors")
async def investor_dues():
    """Per investor and type: paid vs owed (from requests) up to the current month.

    Every investor is returned; `types` has the types they paid for, owe, or are assigned to.
    """
    now = datetime.now(PKT)
    as_of = f"{now.year}-{now.month:02d}"
    current = month_index(as_of)

    owed: dict[tuple[str, str], float] = {}
    async for r in db.requests.find():
        n = months_due(r, current)
        for inv in r["investor_ids"]:
            owed[(inv, r["type_id"])] = owed.get((inv, r["type_id"]), 0) + n * r["amount"]

    paid: dict[tuple[str, str], float] = {}
    async for d in db.investments.find():
        key = (d["investor_id"], d["type_id"])
        paid[key] = paid.get(key, 0) + d["amount"]

    type_names = {str(t["_id"]): t["name"] async for t in db.investment_types.find()}
    out = []
    async for i in db.investors.find().sort("name", 1):
        iid = str(i["_id"])
        assigned = set(i.get("type_ids", []))
        types = []
        for tid, tname in type_names.items():
            p, o = paid.get((iid, tid), 0), owed.get((iid, tid), 0)
            if p or o or tid in assigned:
                types.append({
                    "id": tid, "name": tname, "paid": p, "owed": o,
                    "remaining": max(0, o - p), "ahead": max(0, p - o),
                })
        out.append({"id": iid, "name": i["name"], "types": types})
    return {"as_of": as_of, "investors": out}
