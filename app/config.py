from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    supabase_url: str
    supabase_service_key: str
    supabase_storage_bucket: str = "gn-tech-uploads"
    allowed_origins: str = "http://localhost:5173"
    admin_token: str = "changeme"

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    class Config:
        env_file = ".env"


settings = Settings()
