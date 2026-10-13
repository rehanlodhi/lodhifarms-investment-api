from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    mongo_url: str = "mongodb://localhost:27017"
    mongo_db: str = "lodhifarms_investment"
    jwt_secret: str  # required; set in .env
    jwt_expire_minutes: int = 60 * 24
    admin_email: str = "admin@lodhifarms.com"
    admin_password: str  # required; set in .env
    cors_origins: list[str] = ["http://localhost:4200"]
    upload_dir: Path = Path("uploads")
    max_upload_mb: int = 10


settings = Settings()
