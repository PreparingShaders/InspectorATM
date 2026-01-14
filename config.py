from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    BOT_TOKEN: str
    ADMIN_ID: int
    DATABASE_URL: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()


# Константы проекта
ATM_PATTERN = r"\b\d{6}\b"         # можно легко расширить/изменить
NOTIFY_ADMIN_ON_NEW_REPORT = True