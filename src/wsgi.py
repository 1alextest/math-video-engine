"""WSGI entry point for production deployment.

Usage:
    gunicorn -w 2 -b 0.0.0.0:5000 --timeout 300 src.wsgi:app
"""

import signal
import sys
from pathlib import Path

# Add src to path so imports work when run from repo root
sys.path.insert(0, str(Path(__file__).parent))

from main import app
from video_generator import stop_all_workers


def _handle_signal(signum, frame):
    """Graceful shutdown: stop all rendering threads before exit."""
    print(f"[SHUTDOWN] Received signal {signum}, stopping background jobs...")
    stop_all_workers(timeout=10.0)
    sys.exit(0)


signal.signal(signal.SIGTERM, _handle_signal)
signal.signal(signal.SIGINT, _handle_signal)

# Export the WSGI application
application = app
