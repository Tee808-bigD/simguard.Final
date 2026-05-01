from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    integration_mode: str = "SIMULATION"

    nac_api_key: str = ""
    anthropic_api_key: str = ""

    database_url: str = "sqlite:///./simguard.db"

    app_env: str = "development"
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    rate_limit_per_minute: int = 60
    auth_rate_limit_per_minute: int = 10

    nac_auth_clientcredentials_url: str = "https://nac-authorization-server.p-eu.rapidapi.com"
    nac_auth_clientcredentials_host: str = "nac-authorization-server.nokia.rapidapi.com"
    nac_wellknown_metadata_url: str = "https://well-known-metadata.p-eu.rapidapi.com"
    nac_wellknown_metadata_host: str = "well-known-metadata.nokia.rapidapi.com"
    nac_number_verification_url: str = "https://number-verification.p-eu.rapidapi.com"
    nac_number_verification_host: str = "number-verification.nokia.rapidapi.com"

    max_payload_size: int = 1_048_576

    @field_validator("integration_mode")
    @classmethod
    def validate_integration_mode(cls, value: str) -> str:
        normalized = value.strip().upper()
        allowed = {"AUTO", "SIMULATION", "LIVE"}
        if normalized not in allowed:
            raise ValueError(f"INTEGRATION_MODE must be one of: {', '.join(sorted(allowed))}")
        return normalized

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    class Config:
        env_file = Path(__file__).resolve().parents[2] / ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
