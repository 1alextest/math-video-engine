"""Video length, style, and quality presets for consistent output."""

SCENE_DURATION_LECTURE = 12
SCENE_DURATION_QUICK = 8

# Legacy keys mapped to new preset ids
LENGTH_ALIASES = {
    "long": "min_2",
    "extended": "min_2",
    "lecture_5": "min_5",
    "lecture_10": "min_10",
    "lecture_20": "min_20",
    "lecture_30": "min_30",
}


def _lecture_preset(minutes: int) -> dict:
    duration_sec = minutes * 60
    scene_count = max(4, round(duration_sec / SCENE_DURATION_LECTURE))
    return {
        "label": f"{minutes} min",
        "duration_sec": duration_sec,
        "duration_min": minutes,
        "scene_count": scene_count,
        "scene_duration_sec": SCENE_DURATION_LECTURE,
        "max_sentences": 3 if minutes <= 2 else 4,
        "group": "lecture",
    }


LENGTH_PRESETS = {
    "short": {
        "label": "Quick (~45s)",
        "duration_sec": 45,
        "duration_min": 1,
        "scene_count": 5,
        "scene_duration_sec": SCENE_DURATION_QUICK,
        "max_sentences": 2,
        "group": "quick",
    },
    "standard": {
        "label": "Quick (~1 min)",
        "duration_sec": 60,
        "duration_min": 1,
        "scene_count": 7,
        "scene_duration_sec": SCENE_DURATION_QUICK,
        "max_sentences": 2,
        "group": "quick",
    },
    "min_2": _lecture_preset(2),
    "min_5": _lecture_preset(5),
    "min_10": _lecture_preset(10),
    "min_15": _lecture_preset(15),
    "min_20": _lecture_preset(20),
    "min_25": _lecture_preset(25),
    "min_30": _lecture_preset(30),
}

STYLE_PRESETS = {
    "balanced": {
        "label": "Balanced",
        "audience": "general audience",
        "tone": "clear, engaging, and approachable",
        "visual_style": (
            "Dark navy background (#1a1a2e). White titles. Accent colors: BLUE for "
            "highlights, YELLOW for emphasis, GREEN for positive results. Use consistent "
            "font sizes: large titles (scale 1.2), body text (scale 0.8). Each scene "
            "opens with a brief title fade-in, then main content. End scenes with a "
            "0.3s pause before transitioning."
        ),
    },
    "beginner": {
        "label": "Beginner-friendly",
        "audience": "students new to the topic",
        "tone": "simple, friendly, and step-by-step with analogies",
        "visual_style": (
            "Dark background (#1a1a2e). Large readable text. Use simple shapes and "
            "minimal elements per scene. BLUE and WHITE only for core content, YELLOW "
            "for key terms. Avoid clutter — max 3 visual elements on screen at once."
        ),
    },
    "technical": {
        "label": "Technical / exam prep",
        "audience": "advanced learners",
        "tone": "precise, rigorous, and terminology-focused",
        "visual_style": (
            "Dark background (#0f0f1a). WHITE equations and labels. BLUE for definitions, "
            "RED for warnings or edge cases. Include formulas where relevant. Structured "
            "layout: title top-left, diagram center, notes bottom."
        ),
    },
}

QUALITY_PRESETS = {
    "preview": {
        "label": "Preview (fast)",
        "manim_flag": "-ql",
        "output_subdir": "480p15",
    },
    "standard": {
        "label": "Standard",
        "manim_flag": "-qm",
        "output_subdir": "720p30",
    },
    "high": {
        "label": "High quality",
        "manim_flag": "-qh",
        "output_subdir": "1080p60",
    },
}


def resolve_length_key(length_key: str) -> str:
    if length_key in LENGTH_PRESETS:
        return length_key
    return LENGTH_ALIASES.get(length_key, "standard")


def normalize_video_settings(raw=None):
    """Merge user options with defaults."""
    raw = raw or {}
    length_key = resolve_length_key(raw.get("length") or raw.get("video_length") or "standard")
    style_key = raw.get("style") or raw.get("video_style") or "balanced"
    quality_key = raw.get("quality") or raw.get("video_quality") or "standard"

    if style_key not in STYLE_PRESETS:
        style_key = "balanced"
    if quality_key not in QUALITY_PRESETS:
        quality_key = "standard"

    return {
        "length": length_key,
        "style": style_key,
        "quality": quality_key,
        "review_script": bool(raw.get("review_script", True)),
        "length_preset": LENGTH_PRESETS[length_key],
        "style_preset": STYLE_PRESETS[style_key],
        "quality_preset": QUALITY_PRESETS[quality_key],
    }


def get_settings_options():
    """Options for the frontend."""
    quick = []
    lecture = []
    for key, preset in LENGTH_PRESETS.items():
        entry = {
            "id": key,
            "label": preset["label"],
            "duration_min": preset.get("duration_min"),
            "scene_count": preset["scene_count"],
        }
        if preset.get("group") == "lecture":
            lecture.append(entry)
        else:
            quick.append(entry)

    return {
        "lengths": quick + lecture,
        "length_groups": [
            {"label": "Quick tests", "lengths": quick},
            {"label": "Full length", "lengths": lecture},
        ],
        "styles": [{"id": key, "label": preset["label"]} for key, preset in STYLE_PRESETS.items()],
        "qualities": [
            {"id": key, "label": preset["label"]} for key, preset in QUALITY_PRESETS.items()
        ],
    }
