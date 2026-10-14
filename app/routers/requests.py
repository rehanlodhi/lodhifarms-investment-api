from fastapi import APIRouter, HTTPException

from ..db import db
from ..models import RequestIn, serialize
from ..security import CurrentUser
from .crud import oid

router = APIRouter(prefix="/requests", tags=["requests"], dependencies=[CurrentUser])


async def validate_refs(body: RequestIn):
    if not await db.investment_types.find_one({"_id": oid(body.type_id)}):
        raise HTTPException(422, "Unknown investment type")
    found = await db.investors.count_documents({"_id": {"$in": [oid(i) for i in body.investor_ids]}})
    if found != len(set(body.investor_ids)):
        raise HTTPException(422, "Unknown investor in list")


@router.get("")
async def list_requests():
    return [serialize(d) async for d in db.requests.find().sort([("start_month", -1)])]


@router.post("", status_code=201)
async def create(body: RequestIn):
    await validate_refs(body)
    doc = body.model_dump()
    doc["investor_ids"] = list(dict.fromkeys(doc["investor_ids"]))
    res = await db.requests.insert_one(doc)
    doc["_id"] = res.inserted_id
    return serialize(doc)


@router.put("/{item_id}")
async def update(item_id: str, body: RequestIn):
    await validate_refs(body)
    doc = body.model_dump()
    doc["investor_ids"] = list(dict.fromkeys(doc["investor_ids"]))
    res = await db.requests.find_one_and_update({"_id": oid(item_id)}, {"$set": doc}, return_document=True)
    if not res:
        raise HTTPException(404, "Not found")
    return serialize(res)


@router.delete("/{item_id}", status_code=204)
async def delete(item_id: str):
    await db.requests.delete_one({"_id": oid(item_id)})
