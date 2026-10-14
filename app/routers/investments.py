import uuid
from datetime import date, datetime, timezone
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from ..config import settings
from ..db import db
from ..models import BulkDeleteIn, BulkInvestmentIn
from ..security import CurrentUser
from .crud import oid
from ..models import serialize

router = APIRouter(prefix="/investments", tags=["investments"], dependencies=[CurrentUser])

ALLOWED = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp", "image/gif": ".gif"}


async def save_files(files: list[UploadFile]) -> list[str]:
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    saved = []
    for f in files:
        ext = ALLOWED.get(f.content_type or "")
        if not ext:
            raise HTTPException(415, f"Unsupported file type: {f.filename}")
        data = await f.read()
        if len(data) > settings.max_upload_mb * 1024 * 1024:
            raise HTTPException(413, f"{f.filename} is too large")
        name = f"{uuid.uuid4().hex}{ext}"
        (settings.upload_dir / name).write_bytes(data)
        saved.append(name)
    return saved


async def validate_refs(investor_id: str, type_id: str):
    if not await db.investors.find_one({"_id": oid(investor_id)}):
        raise HTTPException(422, "Unknown investor")
    if not await db.investment_types.find_one({"_id": oid(type_id)}):
        raise HTTPException(422, "Unknown investment type")


@router.get("")
async def list_investments():
    investors = {str(d["_id"]): d["name"] async for d in db.investors.find()}
    types = {str(d["_id"]): d["name"] async for d in db.investment_types.find()}
    out = []
    async for d in db.investments.find().sort("date", -1):
        d = serialize(d)
        d["investor_name"] = investors.get(d["investor_id"], "?")
        d["type_name"] = types.get(d["type_id"], "?")
        out.append(d)
    return out


@router.post("/bulk", status_code=201)
async def bulk_create(body: BulkInvestmentIn):
    investor_ids = list(dict.fromkeys(body.investor_ids))
    if not await db.investment_types.find_one({"_id": oid(body.type_id)}):
        raise HTTPException(422, "Unknown investment type")
    found = await db.investors.count_documents({"_id": {"$in": [oid(i) for i in investor_ids]}})
    if found != len(investor_ids):
        raise HTTPException(422, "Unknown investor in list")

    month = body.month or body.date.isoformat()[:7]
    created = skipped = 0
    for investor_id in investor_ids:
        key = {"investor_id": investor_id, "type_id": body.type_id, "month": month, "amount": body.amount}
        if body.skip_existing and await db.investments.find_one(key):
            skipped += 1
            continue
        await db.investments.insert_one({
            **key, "date": body.date.isoformat(), "note": body.note, "screenshots": [],
            "created_at": datetime.now(timezone.utc),
        })
        created += 1
    return {"created": created, "skipped": skipped}


@router.post("/bulk-delete")
async def bulk_delete(body: BulkDeleteIn):
    ids = [oid(i) for i in dict.fromkeys(body.ids)]
    docs = await db.investments.find({"_id": {"$in": ids}}).to_list(None)
    await db.investments.delete_many({"_id": {"$in": ids}})
    for doc in docs:
        for name in doc.get("screenshots", []):
            (settings.upload_dir / Path(name).name).unlink(missing_ok=True)
    return {"deleted": len(docs)}


@router.post("", status_code=201)
async def create(
    investor_id: str = Form(),
    type_id: str = Form(),
    amount: float = Form(gt=0),
    date_: date = Form(alias="date"),
    month: str | None = Form(None, pattern=r"^\d{4}-\d{2}$"),
    note: str | None = Form(None),
    screenshots: list[UploadFile] = File(default=[]),
):
    await validate_refs(investor_id, type_id)
    doc = {
        "investor_id": investor_id,
        "type_id": type_id,
        "amount": amount,
        "date": date_.isoformat(),
        "month": month or date_.isoformat()[:7],
        "note": note,
        "screenshots": await save_files(screenshots),
        "created_at": datetime.now(timezone.utc),
    }
    res = await db.investments.insert_one(doc)
    doc["_id"] = res.inserted_id
    return serialize(doc)


@router.put("/{item_id}")
async def update(
    item_id: str,
    investor_id: str = Form(),
    type_id: str = Form(),
    amount: float = Form(gt=0),
    date_: date = Form(alias="date"),
    month: str | None = Form(None, pattern=r"^\d{4}-\d{2}$"),
    note: str | None = Form(None),
    screenshots: list[UploadFile] = File(default=[]),
):
    """Updates fields and appends any newly uploaded screenshots."""
    await validate_refs(investor_id, type_id)
    new = await save_files(screenshots)
    res = await db.investments.find_one_and_update(
        {"_id": oid(item_id)},
        {
            "$set": {
                "investor_id": investor_id,
                "type_id": type_id,
                "amount": amount,
                "date": date_.isoformat(),
                "month": month or date_.isoformat()[:7],
                "note": note,
            },
            "$push": {"screenshots": {"$each": new}},
        },
        return_document=True,
    )
    if not res:
        raise HTTPException(404, "Not found")
    return serialize(res)


@router.post("/{item_id}/screenshots")
async def add_screenshots(item_id: str, screenshots: list[UploadFile] = File()):
    new = await save_files(screenshots)
    res = await db.investments.find_one_and_update(
        {"_id": oid(item_id)}, {"$push": {"screenshots": {"$each": new}}}, return_document=True
    )
    if not res:
        raise HTTPException(404, "Not found")
    return serialize(res)


@router.put("/{item_id}/screenshots/{name}")
async def replace_screenshot(item_id: str, name: str, screenshot: UploadFile = File()):
    doc = await db.investments.find_one({"_id": oid(item_id)})
    if not doc or name not in doc.get("screenshots", []):
        raise HTTPException(404, "Not found")
    (new,) = await save_files([screenshot])
    shots = [new if n == name else n for n in doc["screenshots"]]
    await db.investments.update_one({"_id": doc["_id"]}, {"$set": {"screenshots": shots}})
    (settings.upload_dir / Path(name).name).unlink(missing_ok=True)
    return serialize({**doc, "screenshots": shots})


@router.delete("/{item_id}/screenshots/{name}", status_code=204)
async def delete_screenshot(item_id: str, name: str):
    res = await db.investments.update_one({"_id": oid(item_id)}, {"$pull": {"screenshots": name}})
    if not res.matched_count:
        raise HTTPException(404, "Not found")
    (settings.upload_dir / Path(name).name).unlink(missing_ok=True)


@router.delete("/{item_id}", status_code=204)
async def delete(item_id: str):
    doc = await db.investments.find_one_and_delete({"_id": oid(item_id)})
    for name in (doc or {}).get("screenshots", []):
        (settings.upload_dir / Path(name).name).unlink(missing_ok=True)
