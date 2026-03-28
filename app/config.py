"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """App settings from .env file."""

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./skinvise.db"

    # App
    APP_NAME: str = "SkinVise AI Engine"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # CORS
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:8000"

    # Image Validation
    MAX_IMAGE_SIZE_MB: int = 10
    MIN_BRIGHTNESS: int = 40
    MAX_BRIGHTNESS: int = 220
    MIN_SHARPNESS: float = 50.0

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()
