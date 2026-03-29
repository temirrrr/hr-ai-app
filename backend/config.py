from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "KMG HR AI Command Center"
    data_dir: Path = Field(
        default_factory=lambda: Path(__file__).resolve().parents[1] / "data"
    )
    cache_dir: Path = Field(
        default_factory=lambda: Path(__file__).resolve().parent / ".cache"
    )
    cache_version: str = "v3"
    llm_api_key: str | None = None
    llm_base_url: str | None = None
    llm_model: str = "gpt-4.1-mini"
    llm_timeout_seconds: float = 20.0


settings = Settings()
