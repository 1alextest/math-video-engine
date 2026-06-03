# Deployment Guide

## Quick Start (Docker Compose)

```bash
# 1. Clone and enter the repo
git clone https://github.com/1alextest/math-video-engine.git
cd math-video-engine

# 2. Copy environment template
cp .env.example .env
# Edit .env and add your API keys

# 3. Build and run
docker-compose up --build -d

# 4. Check health
curl http://localhost:5000/api/health
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | **Yes*** | For GPT-4o / GPT-4 / embeddings |
| `CLAUDE_API_KEY` | **Yes*** | For Claude 3 Opus/Sonnet |
| `OLLAMA_BASE_URL` | No | Local Ollama URL (default: `http://localhost:11434`) |
| `ELEVENLABS_API_KEY` | No | For premium TTS voices |
| `SUPABASE_URL` | No | Cloud database URL |
| `SUPABASE_KEY` | No | Cloud database service key |
| `PORT` | No | Server port (default: `5000`) |

\* At least one LLM provider must be configured.

## Docker Compose Options

### With local Ollama (no cloud API keys)

Uncomment the `ollama` service in `docker-compose.yml`, then:

```bash
docker-compose up -d ollama
# Pull a model
docker-compose exec ollama ollama pull llama3.2
# Start the app
docker-compose up -d app
```

Set `.env`:
```
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_MODEL=llama3.2
```

### With GPU acceleration

Uncomment the GPU reservation block in `docker-compose.yml` under the `ollama` service.

## Railway / Render / Fly.io

### Railway

1. Connect your GitHub repo
2. Add environment variables in the Railway dashboard
3. Set start command: `gunicorn -w 2 -b 0.0.0.0:$PORT --timeout 300 src.wsgi:application`
4. Add a volume mount for `/app/media` to persist videos

### Render

1. Create a new Web Service from your GitHub repo
2. Set:
   - **Build Command**: `pip install -e .`
   - **Start Command**: `gunicorn -w 2 -b 0.0.0.0:$PORT --timeout 300 src.wsgi:application`
3. Add a disk mount at `/app/media` (minimum 5GB)
4. Add environment variables

### Fly.io

```bash
fly launch --dockerfile Dockerfile
fly volumes create media_data --size 10
# Edit fly.toml to mount volume at /app/media
fly deploy
```

## Production Checklist

- [ ] At least one LLM API key configured
- [ ] TTS provider configured (or TTS disabled)
- [ ] Persistent volume for `/app/media`
- [ ] Persistent volume for `/app/content`
- [ ] Health check endpoint monitored (`/api/health`)
- [ ] Memory limit ≥ 2GB (4GB recommended)
- [ ] Graceful shutdown timeout ≥ 60s (rendering threads need time)
- [ ] `.env` not committed to git

## Monitoring

The health endpoint returns:

```json
{
  "status": "healthy",
  "manim": {"manim_available": true, ...},
  "providers": {"llm_ready": true, "tts_ready": true},
  "disk": {"media_free_gb": 45.2},
  "snippets": 12
}
```

Watch for `status: "degraded"` — this means Manim or LLM is unavailable.

## Troubleshooting

**Container exits immediately**: Check `docker logs topic2manim` for missing env vars.

**Videos not persisting**: Ensure the `media_data` Docker volume is mounted.

**Ollama connection refused**: Use `http://ollama:11434` (service name) inside Docker, not `localhost`.

**Out of memory**: Increase Docker memory limit to 4GB+ — Manim rendering is memory-intensive.
