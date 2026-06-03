"""Helpers for resuming interrupted render jobs from checkpoints."""

from render_pipeline import load_checkpoint

RESUMABLE_STATUSES = frozenset({"failed", "interrupted", "cancelled"})


def job_can_resume(job: dict | None) -> bool:
    """True when a job has saved render progress and may resume rendering."""
    if not job:
        return False
    if job.get("status") not in RESUMABLE_STATUSES:
        return False
    script = job.get("script") or []
    if not script:
        return False

    checkpoint = load_checkpoint(job)
    scene_videos = checkpoint.get("scene_videos") or {}
    scene_codes = checkpoint.get("scene_codes") or {}
    # Use rendered files only; job.scenes_done tracks codegen/fix progress, not MP4 output.
    scenes_done = len(scene_videos)
    has_audio = bool(checkpoint.get("audio_path"))
    has_codes = any(
        isinstance(entry, dict) and entry.get("content")
        for entry in scene_codes.values()
    )
    scenes_total = int(job.get("scenes_total") or len(script))

    if scenes_done <= 0 and not has_audio and not has_codes:
        return False
    if scenes_total > 0 and scenes_done >= scenes_total:
        return False
    return True


def enrich_job_for_api(job: dict) -> dict:
    """Add resume metadata for progress/history API responses."""
    payload = dict(job)
    can = job_can_resume(job)
    payload["can_resume"] = can
    payload["resumable"] = can
    if can:
        checkpoint = load_checkpoint(job)
        payload["scenes_done"] = payload.get("scenes_done") or len(
            checkpoint.get("scene_videos") or {}
        )
        payload["scenes_total"] = payload.get("scenes_total") or len(job.get("script") or [])
    return payload
