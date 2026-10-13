from pymongo import AsyncMongoClient

from .config import settings

client = AsyncMongoClient(settings.mongo_url)
db = client[settings.mongo_db]
