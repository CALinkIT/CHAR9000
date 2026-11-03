from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

app = FastAPI(title="CHAR9000 Pydantic-AI Service")

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")

ollama_provider = OpenAIProvider(base_url=f"{OLLAMA_BASE_URL}/v1", api_key="ollama")

# Same model as CrewAI's main agents so the 24 GB GPU keeps one model resident.
MODEL_MAIN = os.getenv("CHAR9000_MODEL_MAIN", "qwen3.6:27b")
classify_model = OpenAIChatModel(MODEL_MAIN, provider=ollama_provider)
extract_model = OpenAIChatModel(MODEL_MAIN, provider=ollama_provider)
summarize_model = OpenAIChatModel(MODEL_MAIN, provider=ollama_provider)


# --- Classification ---

class ClassificationResult(BaseModel):
    category: str = Field(description="One of: inspection_report, proposal, correspondence, technical_drawing, maintenance_log, specification")
    confidence: float = Field(description="Confidence score between 0 and 1")
    subcategory: str = Field(description="More specific subcategory within the main category")


class ClassifyRequest(BaseModel):
    text: str


classify_agent = Agent(
    classify_model,
    output_type=ClassificationResult,
    retries=3,
    system_prompt=(
        "You are a document classifier for an industrial facility. "
        "Classify the given text into exactly one category: inspection_report, proposal, "
        "correspondence, technical_drawing, maintenance_log, or specification. "
        "Also provide a confidence score (0-1) and a more specific subcategory. "
        "You MUST provide ALL three fields: category, confidence, and subcategory."
    ),
)


@app.post("/classify")
async def classify(req: ClassifyRequest) -> ClassificationResult:
    try:
        result = await classify_agent.run(req.text)
        return result.output
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Extraction ---

class ExtractionResult(BaseModel):
    extracted: dict[str, str | None] = Field(description="Extracted field values")


class ExtractRequest(BaseModel):
    text: str
    fields: list[str] = Field(
        default_factory=lambda: [
            "facility_name", "date", "inspector", "findings", "severity", "recommendations"
        ]
    )


extract_agent = Agent(
    extract_model,
    output_type=ExtractionResult,
    retries=3,
    system_prompt=(
        "You are a data extraction agent for industrial inspection reports. "
        "Extract the requested fields from the given text. "
        "Return null for any field that cannot be found in the text. "
        "You MUST return a dict with the key 'extracted' containing the field values."
    ),
)


@app.post("/extract")
async def extract(req: ExtractRequest) -> ExtractionResult:
    try:
        prompt = f"Extract these fields: {', '.join(req.fields)}\n\nText:\n{req.text}"
        result = await extract_agent.run(prompt)
        return result.output
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Summarization ---

class SummaryResult(BaseModel):
    summary: str = Field(description="Concise summary of the text")
    key_points: list[str] = Field(description="Key points from the text")


class SummarizeRequest(BaseModel):
    text: str
    max_length: int = 200


summarize_agent = Agent(
    summarize_model,
    output_type=SummaryResult,
    retries=3,
    system_prompt=(
        "You are a summarization agent for industrial facility documents. "
        "Provide a concise summary and extract key points from the given text. "
        "You MUST provide both fields: summary and key_points."
    ),
)


@app.post("/summarize")
async def summarize(req: SummarizeRequest) -> SummaryResult:
    try:
        prompt = f"Summarize the following text in at most {req.max_length} words:\n\n{req.text}"
        result = await summarize_agent.run(prompt)
        return result.output
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Health ---

@app.get("/health")
async def health():
    return {"status": "ok"}
