"""VLM frame critic — verify rendered frames match narration and visual events."""

import base64
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from env_loader import load_app_env
from json_utils import extract_json_from_llm_response
from llm_chat import complete_llm_vision
from visual_events import format_events_for_prompt

_PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _safe_project_path(path: str, label: str = "path") -> str:
    """Validate that a path is within the project root (prevents traversal attacks)."""
    if not path or not isinstance(path, str):
        raise ValueError(f"Invalid {label}: must be a non-empty string")
    resolved = Path(path).resolve()
    try:
        resolved.relative_to(_PROJECT_ROOT)
    except ValueError:
        raise ValueError(f"Invalid {label}: must be inside project directory")
    if "\x00" in path:
        raise ValueError(f"Invalid {label}: contains null bytes")
    return str(resolved)


def is_critic_enabled() -> bool:
    load_app_env()
    return os.getenv("ENABLE_FRAME_CRITIC", "true").lower() not in ("0", "false", "no")


def critic_min_score() -> float:
    load_app_env()
    try:
        return float(os.getenv("CRITIC_MIN_SCORE", "6"))
    except ValueError:
        return 6.0


def critic_max_retries() -> int:
    load_app_env()
    try:
        return int(os.getenv("CRITIC_MAX_RETRIES", "2"))
    except ValueError:
        return 2


def extract_video_frames(video_path: str, count: int = 3) -> List[str]:
    """Extract JPEG frames from a scene video using ffmpeg."""
    try:
        video_path = _safe_project_path(video_path, "video_path")
    except ValueError:
        return []
    if not os.path.isfile(video_path):
        return []

    abs_path = str(Path(video_path).resolve())
    temp_dir = tempfile.mkdtemp(prefix="t2m_frames_")

    try:
        probe = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                abs_path,
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        duration = float(probe.stdout.strip() or "5")
    except Exception:
        duration = 5.0

    timestamps = []
    if count <= 1:
        timestamps = [max(duration * 0.5, 0.1)]
    else:
        for i in range(count):
            ratio = (i + 1) / (count + 1)
            timestamps.append(max(duration * ratio, 0.1))

    frames = []
    for index, ts in enumerate(timestamps, 1):
        out_file = os.path.join(temp_dir, f"frame_{index:02d}.jpg")
        cmd = [
            "ffmpeg",
            "-y",
            "-ss",
            str(ts),
            "-i",
            abs_path,
            "-frames:v",
            "1",
            "-q:v",
            "2",
            out_file,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode == 0 and os.path.isfile(out_file):
            frames.append(out_file)

    return frames


def _encode_image(path: str) -> str:
    with open(path, "rb") as handle:
        return base64.standard_b64encode(handle.read()).decode("ascii")


def critique_scene_frames(
    client,
    provider: str,
    model: str,
    frame_paths: List[str],
    narration: str,
    animation: str,
    visual_events: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Ask a vision-capable LLM whether frames match the intended scene.

    Returns: {ok, score, issues, suggestions}
    """
    if not frame_paths:
        return {"ok": True, "score": 10, "issues": [], "suggestions": "", "skipped": True}

    events_block = format_events_for_prompt(visual_events or [])
    prompt = f"""You are reviewing frames from an educational math animation video.

NARRATION (what the viewer hears):
{narration}

INTENDED ANIMATION:
{animation}

REQUIRED VISUAL EVENTS (each should be visible or clearly implied):
{events_block}

Score alignment from 0-10 where:
- 10 = perfectly matches narration and visual events
- 7-9 = good, minor issues
- 4-6 = partially matches, noticeable gaps
- 0-3 = wrong, missing, or misleading visuals

Respond ONLY with JSON:
{{
  "score": 8,
  "issues": ["list of specific problems"],
  "suggestions": "how to fix the Manim animation",
  "ok": true
}}

Set ok=true if score >= {critic_min_score()}, else ok=false."""

    images_b64 = [_encode_image(path) for path in frame_paths[:3]]
    try:
        response = complete_llm_vision(
            client=client,
            provider=provider,
            model=model,
            system_prompt="You evaluate educational math video frames for alignment with narration.",
            user_prompt=prompt,
            images_base64=images_b64,
        )
        parsed = extract_json_from_llm_response(response)
        score = float(parsed.get("score", 0))
        ok = bool(parsed.get("ok", score >= critic_min_score()))
        return {
            "ok": ok,
            "score": score,
            "issues": parsed.get("issues") or [],
            "suggestions": parsed.get("suggestions") or "",
            "skipped": False,
        }
    except Exception as exc:
        print(f"[CRITIC] Vision critique skipped: {exc}")
        return {
            "ok": True,
            "score": 10,
            "issues": [],
            "suggestions": "",
            "skipped": True,
            "error": str(exc),
        }


def build_critic_fix_prompt(original_code: str, critique: Dict[str, Any], narration: str) -> str:
    issues = critique.get("issues") or []
    suggestions = critique.get("suggestions") or ""
    return f"""The rendered video frames do NOT match the intended educational content.

NARRATION: {narration}

ISSUES FOUND:
{json.dumps(issues, indent=2)}

SUGGESTED FIXES:
{suggestions}

Fix the Manim code below to address these visual alignment issues.
Keep the same class name and overall structure where possible.

CURRENT CODE:
```python
{original_code}
```

Respond ONLY with JSON:
{{"content": "fixed python code", "class_name": "SameClassName", "fix_explanation": "what changed"}}
"""
