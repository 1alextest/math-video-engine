"""Tests for env_loader path resolution."""

import os
from unittest.mock import patch

from env_loader import get_env, load_app_env


def test_env_path_exists():
    """env_loader looks for .env next to project root."""
    from env_loader import ENV_PATH

    assert ENV_PATH.name == ".env"


def test_load_app_env_runs_without_error():
    load_app_env()  # should not raise


def test_get_env_reads_existing():
    with patch.dict(os.environ, {"TEST_VAR_12345": "hello"}, clear=False):
        assert get_env("TEST_VAR_12345") == "hello"


def test_get_env_default():
    assert get_env("NONEXISTENT_VAR_XYZ", "fallback") == "fallback"


def test_get_env_none_default():
    assert get_env("NONEXISTENT_VAR_XYZ") is None
