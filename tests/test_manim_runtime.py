"""Tests for Manim CLI detection."""

from unittest.mock import patch

from manim_runtime import is_manim_available, manim_unavailable_reason, resolve_manim_executable


def test_manim_unavailable_when_not_on_path():
    with patch("manim_runtime.resolve_manim_executable", return_value=None):
        assert is_manim_available() is False
        assert manim_unavailable_reason() is not None


def test_manim_available_when_resolved():
    with patch("manim_runtime.resolve_manim_executable", return_value="/usr/bin/manim"):
        assert is_manim_available() is True
        assert manim_unavailable_reason() is None


def test_manim_status_for_api_when_available():
    from manim_runtime import manim_status_for_api

    with patch("manim_runtime.resolve_manim_executable", return_value="/usr/bin/manim"):
        status = manim_status_for_api()
    assert status["manim_available"] is True
    assert status["manim_executable"] == "/usr/bin/manim"
    assert status["manim_hint"] is None
    assert status["render_backend"] == "local"


def test_manim_status_for_api_when_unavailable():
    from manim_runtime import manim_status_for_api

    with patch("manim_runtime.resolve_manim_executable", return_value=None):
        with patch("manim_runtime.manim_unavailable_reason", return_value="install manim"):
            status = manim_status_for_api()
    assert status["manim_available"] is False
    assert status["manim_executable"] is None
    assert status["manim_hint"] == "install manim"
    assert status["render_backend"] == "unavailable"


def test_compile_video_returns_clear_error_without_manim():
    from pathlib import Path

    from concat_video import compile_video

    root = Path(__file__).resolve().parent.parent
    fake_py = root / "tests" / "tmp" / "no_manim_scene.py"
    fake_py.parent.mkdir(parents=True, exist_ok=True)
    fake_py.write_text("# test\n", encoding="utf-8")
    try:
        with patch("concat_video.resolve_manim_executable", return_value=None):
            path, err = compile_video(str(fake_py), "Scene1", "topic", 1)
        assert path is None
        assert err is not None
        assert "Manim" in err
    finally:
        fake_py.unlink(missing_ok=True)
