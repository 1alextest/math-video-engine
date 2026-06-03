# Multi-stage build for production deployment
# Build: docker build -t topic2manim .
# Run:   docker run -p 5000:5000 --env-file .env topic2manim

# ---------------------------------------------------------------------------
# Stage 1: Dependencies
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS deps

WORKDIR /app

# Install system dependencies for Manim, ffmpeg, and LaTeX
RUN apt-get update && apt-get install -y \
    build-essential \
    libcairo2-dev \
    ffmpeg \
    texlive \
    texlive-latex-extra \
    texlive-fonts-extra \
    texlive-latex-recommended \
    texlive-science \
    tipa \
    libpango1.0-dev \
    pkg-config \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast Python dependency resolution
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy dependency metadata
COPY pyproject.toml README.md .

# Install Python dependencies into the system environment
RUN uv pip install --system .

# ---------------------------------------------------------------------------
# Stage 2: Production image
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS production

WORKDIR /app

# Install runtime system dependencies only (no build tools)
RUN apt-get update && apt-get install -y \
    libcairo2 \
    ffmpeg \
    texlive \
    texlive-latex-extra \
    texlive-fonts-extra \
    texlive-latex-recommended \
    texlive-science \
    tipa \
    libpango1.0-0 \
    pkg-config \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from deps stage
COPY --from=deps /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=deps /usr/local/bin /usr/local/bin

# Copy application code
COPY . .

# Create necessary directories with proper permissions
RUN mkdir -p media public content && chmod 777 media public content

# Expose port
EXPOSE 5000

# Environment
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PORT=5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:5000/api/health || exit 1

# Run with Gunicorn:
# - 2 workers (CPU-bound rendering is done in background threads, not requests)
# - 300s timeout for long-running health checks and preview endpoints
# - Access logs to stdout
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:5000", "--timeout", "300", "--access-logfile", "-", "--error-logfile", "-", "src.wsgi:application"]
