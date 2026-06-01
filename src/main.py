from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import sys
from pathlib import Path

# Add parent directory to path to enable imports
sys.path.insert(0, str(Path(__file__).parent))

from env_loader import load_app_env
from video_generator import (
    start_video_generation,
    get_job_status,
    get_available_llm_providers,
    continue_video_generation,
    update_job_script,
    resume_video_generation,
    cancel_video_generation,
    list_jobs,
    retry_scene_render,
    start_scene_preview,
)
from tts_generator import (
    get_available_tts_providers,
    get_all_tts_providers,
    setup_tts_config,
    get_default_tts_voices,
    list_provider_voices,
)
from llm_providers import (
    get_all_llm_providers,
    setup_llm_client,
    get_default_models,
    list_provider_models,
)
from video_settings import get_settings_options, normalize_video_settings
from provider_health import check_providers
from script_import import parse_import_script
from prompt_template import build_external_script_prompt
from visual_events import get_catalog_for_api

load_app_env()

# Get absolute path to frontend directory
FRONTEND_DIR = Path(__file__).parent / "frontend"

app = Flask(__name__, static_folder=str(FRONTEND_DIR), static_url_path="/static")
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # ISS-0001: 16 MB upload limit
CORS(app)

# Ensure media directory exists (at project root level)
PROJECT_ROOT = Path(__file__).parent.parent
MEDIA_DIR = PROJECT_ROOT / "media"
os.makedirs(MEDIA_DIR, exist_ok=True)


@app.route("/")
def index():
    """Serve the main HTML page"""
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/api/script/prompt-template", methods=["GET"])
def script_prompt_template():
    """Return a copy-paste prompt for ChatGPT / Claude."""
    topic = request.args.get("topic", "")
    length = request.args.get("length", "min_5")
    style = request.args.get("style", "balanced")
    return jsonify(
        {
            "prompt": build_external_script_prompt(topic=topic, length=length, style=style),
            "topic": topic,
            "length": length,
            "style": style,
        }
    )


@app.route("/api/script/parse", methods=["POST"])
def parse_script():
    """Parse pasted script without starting a render job."""
    try:
        data = request.get_json() or {}
        import_script = data.get("import_script") or data.get("script_text")
        if not import_script or not str(import_script).strip():
            return jsonify({"error": "import_script is required"}), 400

        result = parse_import_script(
            str(import_script),
            format_hint=data.get("import_format", "auto"),
            title=data.get("topic") or data.get("title"),
        )
        return jsonify(result)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/generate", methods=["POST"])
def generate_video():
    """Start video generation"""
    try:
        load_app_env()
        data = request.get_json()

        input_mode = data.get("input_mode", "topic")
        import_script = data.get("import_script")
        script = data.get("script")
        import_format = data.get("import_format", "auto")
        enrich_animations = bool(data.get("enrich_animations", False))

        topic = (data.get("topic") or "").strip()

        if input_mode == "import":
            if not import_script and not script:
                return (
                    jsonify({"error": "import_script or script array is required for import mode"}),
                    400,
                )
            if not topic:
                topic = "Imported Video"
        elif not topic:
            return jsonify({"error": "Topic is required"}), 400

        llm_provider = data.get("llm_provider", "auto")
        llm_model = data.get("llm_model")
        tts_provider = data.get("tts_provider", "auto")
        tts_voice = data.get("tts_voice")
        enable_tts = data.get("enable_tts", True)
        video_settings = normalize_video_settings(data.get("video_settings"))

        if enable_tts and tts_provider not in (None, "auto"):
            try:
                setup_tts_config(tts_provider, tts_voice)
            except ValueError as exc:
                return jsonify({"error": str(exc)}), 400

        try:
            setup_llm_client(llm_provider, llm_model)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

        job_id = start_video_generation(
            topic,
            enable_tts,
            llm_provider,
            tts_provider,
            llm_model,
            video_settings,
            tts_voice,
            input_mode=input_mode,
            import_script=import_script,
            script=script,
            import_format=import_format,
            enrich_animations=enrich_animations,
        )

        return (
            jsonify(
                {
                    "job_id": job_id,
                    "status": "queued",
                    "message": "Video generation started",
                    "input_mode": input_mode,
                }
            ),
            202,
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/progress/<job_id>", methods=["GET"])
def get_progress(job_id):
    """Get video generation progress"""
    job = get_job_status(job_id)

    if not job:
        return jsonify({"error": "Job not found"}), 404

    return jsonify(job)


@app.route("/media/<path:filename>")
def serve_media(filename):
    """Serve generated media files"""
    return send_from_directory(MEDIA_DIR, filename)


@app.route("/api/config", methods=["GET"])
def get_config():
    """Return providers available with the current server configuration."""
    load_app_env()
    env_path = Path(__file__).resolve().parent.parent / ".env"
    return jsonify(
        {
            "llm_providers": get_all_llm_providers(),
            "configured_llm_providers": get_available_llm_providers(),
            "tts_providers": get_all_tts_providers(),
            "configured_tts_providers": get_available_tts_providers(),
            "env_file_found": env_path.is_file(),
            "defaults": {
                "llm_provider": os.getenv("LLM_PROVIDER", "auto"),
                "tts_provider": os.getenv("TTS_PROVIDER", "auto"),
                "llm_models": get_default_models(),
                "tts_voices": get_default_tts_voices(),
                "video_settings": {
                    "length": "min_5",
                    "style": "balanced",
                    "quality": "standard",
                    "review_script": True,
                },
            },
            "video_settings_options": get_settings_options(),
            "visual_events": get_catalog_for_api(),
            "features": {
                "frame_critic": os.getenv("ENABLE_FRAME_CRITIC", "true").lower()
                not in ("0", "false", "no"),
                "parallel_workers": os.getenv("RENDER_PARALLEL_WORKERS", "2"),
            },
        }
    )


@app.route("/api/llm/models", methods=["GET"])
def get_llm_models():
    """Return selectable models for a given LLM provider."""
    load_app_env()
    provider = request.args.get("provider", "ollama")
    models = list_provider_models(provider)
    default_model = get_default_models().get(provider)
    return jsonify(
        {
            "provider": provider,
            "models": models,
            "default_model": default_model,
        }
    )


@app.route("/api/tts/voices", methods=["GET"])
def get_tts_voices():
    """Return selectable voices for a TTS provider."""
    load_app_env()
    provider = request.args.get("provider", "elevenlabs")
    voices = list_provider_voices(provider)
    defaults = get_default_tts_voices()
    return jsonify(
        {
            "provider": provider,
            "voices": voices,
            "default_voice": defaults.get(provider),
        }
    )


@app.route("/api/providers/health", methods=["GET", "POST"])
def providers_health():
    """Check whether selected LLM/TTS providers are usable before generating."""
    load_app_env()
    if request.method == "POST":
        data = request.get_json() or {}
    else:
        data = request.args

    results = check_providers(
        llm_provider=data.get("llm_provider", "auto"),
        llm_model=data.get("llm_model"),
        tts_provider=data.get("tts_provider", "auto"),
        tts_voice=data.get("tts_voice"),
        enable_tts=str(data.get("enable_tts", "true")).lower() not in ("0", "false", "no"),
    )
    status_code = 200 if results.get("ready") else 503
    return jsonify(results), status_code


@app.route("/api/jobs/<job_id>/script", methods=["PUT"])
def save_job_script(job_id):
    """Save edited script while job awaits review."""
    try:
        data = request.get_json() or {}
        script = data.get("script")
        if script is None:
            return jsonify({"error": "script is required"}), 400
        validated = update_job_script(job_id, script)
        return jsonify({"ok": True, "script": validated, "scenes": len(validated)})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/jobs", methods=["GET"])
def list_all_jobs():
    """List recent jobs for resume/history UI."""
    limit = min(int(request.args.get("limit", 20)), 50)
    return jsonify({"jobs": list_jobs(limit=limit)})


@app.route("/api/jobs/<job_id>/cancel", methods=["POST"])
def cancel_job(job_id):
    try:
        cancel_video_generation(job_id)
        return jsonify({"ok": True, "status": "cancelled"})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/jobs/<job_id>/scenes/<int:scene_index>/retry", methods=["POST"])
def retry_scene(job_id, scene_index):
    try:
        data = request.get_json() or {}
        retry_scene_render(job_id, scene_index, regen_code=bool(data.get("regen_code")))
        return jsonify({"ok": True, "status": "running"})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/jobs/<job_id>/resume", methods=["POST"])
def resume_job(job_id):
    """Resume an interrupted render from the last checkpoint."""
    try:
        resume_video_generation(job_id)
        return jsonify({"ok": True, "status": "running"})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/preview-scene", methods=["POST"])
def preview_scene():
    """Render a single scene at preview quality before a full run."""
    try:
        load_app_env()
        data = request.get_json() or {}
        script = data.get("script")
        if not script or not isinstance(script, list):
            return jsonify({"error": "script array is required"}), 400

        scene_index = int(data.get("scene_index", 1))
        topic = (data.get("topic") or "").strip() or "Scene Preview"
        enable_tts = bool(data.get("enable_tts", True))
        llm_provider = data.get("llm_provider", "auto")
        llm_model = data.get("llm_model")
        tts_provider = data.get("tts_provider", "auto")
        tts_voice = data.get("tts_voice")
        video_settings = normalize_video_settings(data.get("video_settings"))

        if enable_tts and tts_provider not in (None, "auto"):
            try:
                setup_tts_config(tts_provider, tts_voice)
            except ValueError as exc:
                return jsonify({"error": str(exc)}), 400

        try:
            setup_llm_client(llm_provider, llm_model)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

        job_id = start_scene_preview(
            topic,
            script,
            scene_index=scene_index,
            enable_tts=enable_tts,
            llm_provider=llm_provider,
            tts_provider=tts_provider,
            llm_model=llm_model,
            tts_voice=tts_voice,
            video_settings=video_settings,
        )
        return (
            jsonify(
                {
                    "job_id": job_id,
                    "status": "queued",
                    "message": f"Scene {scene_index} preview started",
                }
            ),
            202,
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/jobs/<job_id>/continue", methods=["POST"])
def continue_job(job_id):
    """Approve script and continue rendering."""
    try:
        data = request.get_json() or {}
        script_override = data.get("script")
        continue_video_generation(job_id, script_override)
        return jsonify({"ok": True, "status": "running"})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "service": "Topic2Manim API"})


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    print("=" * 80)
    print("Topic2Manim Server")
    print("=" * 80)
    print("Starting Flask server...")
    print(f"Access the web interface at: http://localhost:{port}")
    print("=" * 80)
    print("\nNOTE: Auto-reload is disabled to prevent job state loss during video generation")
    print("      Restart the server manually if you make code changes.\n")

    app.run(
        host="0.0.0.0",
        port=port,
        debug=os.getenv("FLASK_DEBUG", "false").lower() in ("true", "1", "yes"),
        use_reloader=False,  # Disable auto-reload to prevent losing job state
        threaded=True,
    )
