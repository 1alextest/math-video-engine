"""Integration tests for render resume and Manim preflight."""

from unittest.mock import patch

import pytest

from job_resume import enrich_job_for_api, job_can_resume
from render_pipeline import empty_checkpoint
from video_generator import (
    get_job_status,
    jobs,
    jobs_lock,
    resume_video_generation,
)


@pytest.fixture(autouse=True)
def clean_jobs():
    from video_generator import _job_threads

    def _drain():
        with jobs_lock:
            for job in list(jobs.values()):
                job["cancel_requested"] = True
        for thread in list(_job_threads.items()):
            if thread.is_alive():
                thread.join(timeout=0.5)
        _job_threads.clear()
        jobs.clear()

    _drain()
    yield
    _drain()


def _failed_job_with_codes_only(job_id="resume-test", scene_count=2):
    script = [{"text": f"Scene {i}", "animation": "fade"} for i in range(1, scene_count + 1)]
    scene_codes = {
        str(i): {
            "class_name": f"Scene{i}",
            "content": f"from manim import *\nclass Scene{i}(Scene):\n    def construct(self): pass",
        }
        for i in range(1, scene_count + 1)
    }
    return {
        "job_id": job_id,
        "status": "failed",
        "topic": "Discount trap",
        "script": script,
        "scenes_total": scene_count,
        "scenes_done": scene_count,
        "enable_tts": False,
        "llm_provider": "openai",
        "error": "No videos were generated",
        "render_checkpoint": {
            **empty_checkpoint(),
            "scene_codes": scene_codes,
            "scene_videos": {},
        },
    }


def test_job_can_resume_ignores_scenes_done_without_videos():
    """Codegen progress (scenes_done) must not block resume when no MP4s exist."""
    job = _failed_job_with_codes_only(scene_count=32)
    assert job["scenes_done"] == 32
    assert len(job["render_checkpoint"]["scene_videos"]) == 0
    assert job_can_resume(job) is True

    enriched = enrich_job_for_api(job)
    assert enriched["can_resume"] is True
    assert enriched["resumable"] is True


@patch("video_generator._resume_worker")
def test_resume_video_generation_accepts_codes_only_checkpoint(mock_worker):
    job_id = "resume-codes-only"
    with jobs_lock:
        jobs[job_id] = _failed_job_with_codes_only(job_id)

    resume_video_generation(job_id)

    mock_worker.assert_called_once_with(job_id)
    status = get_job_status(job_id)
    assert status["status"] == "running"
    assert status.get("error") is None


def test_resume_video_generation_rejects_job_without_codes():
    job_id = "resume-no-codes"
    with jobs_lock:
        jobs[job_id] = {
            "job_id": job_id,
            "status": "failed",
            "topic": "Empty",
            "script": [{"text": "x", "animation": "y"}],
            "render_checkpoint": empty_checkpoint(),
        }

    with pytest.raises(ValueError, match="cannot be resumed"):
        resume_video_generation(job_id)


@patch("manim_runtime.manim_unavailable_reason", return_value="Manim CLI not found.")
def test_render_video_phase_fails_fast_without_manim(mock_reason):
    from video_generator import _render_video_phase

    job_id = "manim-preflight"
    with jobs_lock:
        jobs[job_id] = _failed_job_with_codes_only(job_id)

    with pytest.raises(RuntimeError, match="Manim CLI not found"):
        _render_video_phase(
            job_id,
            "topic",
            jobs[job_id]["script"],
            enable_tts=False,
            llm_config={"client": None, "provider": "openai", "model": "gpt-4o"},
            tts_provider="auto",
            video_settings={"quality": "standard"},
            tts_voice=None,
            content_dir=__import__("pathlib").Path("content"),
            media_dir=__import__("pathlib").Path("media"),
        )
