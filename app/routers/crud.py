from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..db import db
from ..models import serialize
from ..security import CurrentUser


def oid(value: str) -> ObjectId:
    try:
        return ObjectId(value)
    except InvalidId:
        raise HTTPException(404, "Not found")


def crud_router(prefix: str, collection: str, model: type[BaseModel], in_use_field: str) -> APIRouter:
    """List/create/update/delete for a simple collection. Deletion is blocked if investments reference it."""
    router = APIRouter(prefix=prefix, tags=[collection], dependencies=[CurrentUser])
    col = db[collection]

    @router.get("")
    async def list_items():
        return [serialize(d) async for d in col.find().sort("name", 1)]

    @router.post("", status_code=201)
    async def create(body: model):  # type: ignore[valid-type]
        doc = body.model_dump()
        res = await col.insert_one(doc)
        doc["_id"] = res.inserted_id
        return serialize(doc)

    @router.put("/{item_id}")
    async def update(item_id: str, body: model):  # type: ignore[valid-type]
        res = await col.find_one_and_update(
            {"_id": oid(item_id)}, {"$set": body.model_dump()}, return_document=True
        )
        if not res:
            raise HTTPException(404, "Not found")
        return serialize(res)

    @router.delete("/{item_id}", status_code=204)
    async def delete(item_id: str):
        if await db.investments.find_one({in_use_field: item_id}):
            raise HTTPException(409, "Has investments; delete those first")
        await col.delete_one({"_id": oid(item_id)})

    return router
