"""Tests for concat_video hardening and subprocess safety."""

import os
import tempfile
from unittest.mock import MagicMock, patch


from concat_video import (
    compile_video,
    concatenate_videos,
    merge_video_and_audio,
    sanitize_filename,
)


# ---------------------------------------------------------------------------
# sanitize_filename
# ---------------------------------------------------------------------------
def test_sanitize_filename_removes_special_chars():
    assert sanitize_filename("What's Next?") == "Whats Next"


def test_sanitize_filename_collapses_underscores():
    assert sanitize_filename("a__b___c") == "a_b_c"


def test_sanitize_filename_strips_edges():
    assert sanitize_filename("_hello_") == "hello"


# ---------------------------------------------------------------------------
# compile_video
# ---------------------------------------------------------------------------
@patch("video_settings.normalize_video_settings")
def test_compile_video_missing_file(mock_norm):
    mock_norm.return_value = {"quality_preset": {"manim_flag": "-pq", "output_subdir": "720p30"}}
    path, err = compile_video("/nonexistent.py", "Scene1", "test", 1)
    assert path is None
    assert "Source file not found" in err


@patch("video_settings.normalize_video_settings")
def test_compile_video_invalid_class_name(mock_norm):
    mock_norm.return_value = {"quality_preset": {"manim_flag": "-pq", "output_subdir": "720p30"}}
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write("# test")
        temp_path = f.name
    try:
        path, err = compile_video(temp_path, "123Bad", "test", 1)
        assert path is None
        assert "Invalid class name" in err
    finally:
        os.remove(temp_path)


@patch("video_settings.normalize_video_settings")
@patch("concat_video.subprocess.run")
def test_compile_video_success(mock_run, mock_norm):
    mock_norm.return_value = {"quality_preset": {"manim_flag": "-pq", "output_subdir": "720p30"}}
    mock_run.return_value = MagicMock(returncode=0, stderr="")

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write("# test")
        temp_path = f.name
    try:
        path, err = compile_video(temp_path, "Scene1", "topic", 1)
        assert path is not None
        assert err is None
        assert path.endswith("Scene1.mp4")
    finally:
        os.remove(temp_path)


@patch("video_settings.normalize_video_settings")
@patch("concat_video.subprocess.run")
def test_compile_video_failure(mock_run, mock_norm):
    mock_norm.return_value = {"quality_preset": {"manim_flag": "-pq", "output_subdir": "720p30"}}
    mock_run.return_value = MagicMock(returncode=1, stderr="syntax error")

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write("# test")
        temp_path = f.name
    try:
        path, err = compile_video(temp_path, "Scene1", "topic", 1)
        assert path is None
        assert "syntax error" in err
    finally:
        os.remove(temp_path)


@patch("video_settings.normalize_video_settings")
@patch("concat_video.subprocess.run")
def test_compile_video_timeout(mock_run, mock_norm):
    mock_norm.return_value = {"quality_preset": {"manim_flag": "-pq", "output_subdir": "720p30"}}
    from subprocess import TimeoutExpired

    mock_run.side_effect = TimeoutExpired(cmd=["manim"], timeout=300)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write("# test")
        temp_path = f.name
    try:
        path, err = compile_video(temp_path, "Scene1", "topic", 1)
        assert path is None
        assert "Timeout" in err
    finally:
        os.remove(temp_path)


# ---------------------------------------------------------------------------
# concatenate_videos
# ---------------------------------------------------------------------------
def test_concatenate_videos_empty_list():
    assert concatenate_videos([], "out.mp4") is False


@patch("concat_video.subprocess.run")
def test_concatenate_videos_success(mock_run):
    mock_run.return_value = MagicMock(returncode=0, stderr="")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".mp4", delete=False) as f:
        f.write("fake")
        vid = f.name
    try:
        result = concatenate_videos([vid], "out.mp4")
        assert result is True
        # Should create a tempfile list and clean it up
        calls = mock_run.call_args_list
        assert any("concat" in str(c) for c in calls)
    finally:
        if os.path.exists(vid):
            os.remove(vid)


@patch("concat_video.subprocess.run")
def test_concatenate_videos_failure(mock_run):
    mock_run.return_value = MagicMock(returncode=1, stderr="ffmpeg error")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".mp4", delete=False) as f:
        f.write("fake")
        vid = f.name
    try:
        result = concatenate_videos([vid], "out.mp4")
        assert result is False
    finally:
        if os.path.exists(vid):
            os.remove(vid)


# ---------------------------------------------------------------------------
# merge_video_and_audio
# ---------------------------------------------------------------------------
def test_merge_missing_video():
    assert merge_video_and_audio("/no/video.mp4", "/no/audio.mp3", "out.mp4") is False


def test_merge_missing_audio():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".mp4", delete=False) as f:
        f.write("fake")
        vid = f.name
    try:
        assert merge_video_and_audio(vid, "/no/audio.mp3", "out.mp4") is False
    finally:
        os.remove(vid)


@patch("concat_video.subprocess.run")
def test_merge_success(mock_run):
    mock_run.return_value = MagicMock(returncode=0, stderr="")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".mp4", delete=False) as vf:
        vf.write("fakevid")
        vid = vf.name
    with tempfile.NamedTemporaryFile(mode="w", suffix=".mp3", delete=False) as af:
        af.write("fakeaudio")
        aud = af.name
    try:
        assert merge_video_and_audio(vid, aud, "out.mp4") is True
    finally:
        os.remove(vid)
        os.remove(aud)


@patch("concat_video.subprocess.run")
def test_merge_failure(mock_run):
    mock_run.return_value = MagicMock(returncode=1, stderr="codec error")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".mp4", delete=False) as vf:
        vf.write("fakevid")
        vid = vf.name
    with tempfile.NamedTemporaryFile(mode="w", suffix=".mp3", delete=False) as af:
        af.write("fakeaudio")
        aud = af.name
    try:
        assert merge_video_and_audio(vid, aud, "out.mp4") is False
    finally:
        os.remove(vid)
        os.remove(aud)
