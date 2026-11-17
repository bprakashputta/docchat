"""Application settings, loaded from environment variables and the `.env` file.

pydantic-settings reads each field from an env var of the same name (case-insensitive),
validates its type, and fails fast at startup if a required value is missing.
"""

from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Local dev database from docker-compose.yml. Override with DATABASE_URL in .env.
    database_url: str = "postgresql+asyncpg://docchat:docchat@localhost:5433/docchat"

    # API keys are SecretStr so they print as '**********' in logs and tracebacks.
    anthropic_api_key: SecretStr
    voyage_api_key: SecretStr

    # Not needed until Block 2 (EDGAR downloader), so optional for now.
    sec_user_agent: str | None = None

    # LangSmith tracing. The langsmith SDK reads these from the environment itself;
    # they're declared here so the app's config is visible in one place.
    langsmith_tracing: bool = False
    langsmith_project: str = "docchat"


@lru_cache
def get_settings() -> Settings:
    """Build Settings once and reuse it (reading .env on every call would be wasteful)."""
    return Settings()
