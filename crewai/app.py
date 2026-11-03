import asyncio
import os
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Set LiteLLM base URL before importing agents
from config import OLLAMA_BASE_URL
os.environ["OLLAMA_API_BASE"] = OLLAMA_BASE_URL

from agents import build_crew

app = FastAPI(title="CHAR9000 CrewAI Service")
_executor = ThreadPoolExecutor(max_workers=4)


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str = "crewai"
    messages: list[ChatMessage]
    temperature: float = 0.7
    max_tokens: int | None = None


class CrewKickoffRequest(BaseModel):
    message: str


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/v1/models")
@app.get("/models")
async def list_models():
    return {
        "object": "list",
        "data": [
            {
                "id": "crewai",
                "object": "model",
                "created": 1700000000,
                "owned_by": "char9000",
                "name": "CHAR9000 CrewAI",
            }
        ],
    }


@app.post("/v1/chat/completions")
@app.post("/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    user_messages = [m for m in request.messages if m.role == "user"]
    if not user_messages:
        raise HTTPException(status_code=400, detail="No user message found")

    user_message = user_messages[-1].content

    loop = asyncio.get_event_loop()
    try:
        crew = build_crew(user_message)
        result = await loop.run_in_executor(_executor, crew.kickoff)
        response_text = str(result)
    except Exception as e:
        response_text = f"CrewAI execution error: {e}"

    return {
        "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": "crewai",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": response_text},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }


@app.post("/crew/kickoff")
async def crew_kickoff(request: CrewKickoffRequest):
    loop = asyncio.get_event_loop()
    try:
        crew = build_crew(request.message)
        result = await loop.run_in_executor(_executor, crew.kickoff)
        return {"status": "success", "result": str(result)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
