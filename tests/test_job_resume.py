"""Tests for job resume eligibility."""

from job_resume import enrich_job_for_api, job_can_resume
from render_pipeline import empty_checkpoint


def test_job_can_resume_true_with_codes_only():
    job = {
        "status": "failed",
        "script": [{"text": "A"}, {"text": "B"}],
        "scenes_total": 2,
        "render_checkpoint": {
            **empty_checkpoint(),
            "scene_codes": {
                "1": {"class_name": "S1", "content": "from manim import *\nclass S1(Scene): pass"},
            },
        },
    }
    assert job_can_resume(job) is True


def test_job_can_resume_false_without_checkpoint():
    job = {
        "status": "failed",
        "script": [{"text": "Hello", "events": []}],
        "scenes_total": 2,
    }
    assert job_can_resume(job) is False


def test_job_can_resume_true_with_partial_scenes():
    job = {
        "status": "interrupted",
        "script": [{"text": "A"}, {"text": "B"}],
        "scenes_total": 2,
        "render_checkpoint": {
            **empty_checkpoint(),
            "scene_videos": {"0": "/media/scene0.mp4"},
        },
    }
    assert job_can_resume(job) is True
    enriched = enrich_job_for_api(job)
    assert enriched["can_resume"] is True
    assert enriched["scenes_done"] == 1


def test_job_can_resume_false_when_all_scenes_done():
    job = {
        "status": "failed",
        "script": [{"text": "A"}],
        "scenes_total": 1,
        "render_checkpoint": {
            **empty_checkpoint(),
            "scene_videos": {"1": "/media/scene1.mp4"},
        },
    }
    assert job_can_resume(job) is False


def test_job_can_resume_false_for_running_status():
    job = {
        "status": "running",
        "script": [{"text": "A"}],
        "render_checkpoint": {
            **empty_checkpoint(),
            "scene_codes": {"1": {"class_name": "S", "content": "code"}},
        },
    }
    assert job_can_resume(job) is False


def test_enrich_job_for_api_when_not_resumable():
    job = {"status": "completed", "script": [{"text": "done"}]}
    enriched = enrich_job_for_api(job)
    assert enriched["can_resume"] is False
    assert enriched["resumable"] is False
