from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Valorant Stat Phone"
    app_url: str = "http://localhost:8000"
    secret_key: str = "dev-secret-change-me"

    database_url: str = "sqlite:///./valorant_phone.db"

    stats_provider: str = "tracker"  # "tracker" | "riot"

    tracker_api_key: str = ""
    tracker_api_base: str = "https://public-api.tracker.gg"

    riot_client_id: str = ""
    riot_client_secret: str = ""
    riot_redirect_uri: str = "http://localhost:8000/auth/riot/callback"
    riot_oauth_authorize_url: str = "https://auth.riotgames.com/authorize"
    riot_oauth_token_url: str = "https://auth.riotgames.com/token"
    riot_account_region: str = "americas"

    require_device_secret: bool = True

    # Solo desarrollo: vincular Riot ID a mano sin RSO (apagar en produccion)
    dev_allow_manual_link: bool = True


settings = Settings()
