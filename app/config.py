from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Hostel Room Exchange"
    secret_key: str = "change-this-in-production"
    access_token_expire_minutes: int = 120
    database_url: str = "sqlite:///./hostel_exchange.db"
    admin_scholar_numbers: str = ""
    allow_origins: str = "*"

    @property
    def admin_scholar_number_set(self) -> set[str]:
        return {item.strip() for item in self.admin_scholar_numbers.split(",") if item.strip()}

    @property
    def allow_origins_list(self) -> list[str]:
        return [item.strip() for item in self.allow_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
