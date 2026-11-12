"""Application configuration loaded from environment variables."""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    USE_LOCAL_DB = os.getenv("USE_LOCAL_DB", "false").lower() == "true"
    LOCAL_DB_PATH = os.getenv("LOCAL_DB_PATH", os.path.join(os.getcwd(), "local_auth.db"))
    SECRET_KEY = os.getenv("SECRET_KEY")
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_KEY")
    # SUPABASE_KEY is retained as a backwards-compatible alias for older .env files.
    SUPABASE_KEY = SUPABASE_ANON_KEY
    SESSION_COOKIE_NAME = "auth_session"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"
    PERMANENT_SESSION_LIFETIME = 3600
    MAX_CONTENT_LENGTH = 1024 * 1024

    @classmethod
    def validate(cls):
        missing = [name for name in ("SECRET_KEY", "SUPABASE_URL", "SUPABASE_ANON_KEY")
                   if not getattr(cls, name)]
        if missing:
            raise RuntimeError(
                "Missing required environment variables: " + ", ".join(missing) +
                ". Copy .env.example to .env and fill in the values."
            )
