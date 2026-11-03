import os

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
N8N_WEBHOOK_BASE = os.getenv("N8N_WEBHOOK_BASE", "http://n8n:5678/webhook")
QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY") or None
POSTGRES_URL = os.getenv("POSTGRES_URL")  # required; set in docker-compose from .env

# RTX 4090 profile: one 27B model stays resident for planner/researcher/manager so the
# crew does not swap models on the 24 GB GPU; the coder and executor are small.
MODEL_MAIN = os.getenv("CHAR9000_MODEL_MAIN", "qwen3.6:27b")
MODEL_CODER = os.getenv("CHAR9000_MODEL_CODER", "qwen2.5-coder:14b")
MODEL_LIGHT = os.getenv("CHAR9000_MODEL_LIGHT", "gemma3")
