import os
from pathlib import Path

from dotenv import load_dotenv

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"


def load_app_env():
    """Load project .env from a fixed path (works in Docker and local dev)."""
    if ENV_PATH.is_file():
        load_dotenv(dotenv_path=ENV_PATH, override=True)


def get_env(name, default=None):
    load_app_env()
    return os.getenv(name, default)
