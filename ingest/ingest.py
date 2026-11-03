#!/usr/bin/env python3
"""RAG ingestion pipeline: extract text from docs, chunk, embed via Ollama, upsert to Qdrant."""

import argparse
import hashlib
import os
import subprocess
import sys
import uuid
from pathlib import Path

import fitz  # PyMuPDF
import httpx
from docx import Document
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams
from tqdm import tqdm

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".doc", ".txt", ".md"}


def parse_args():
    parser = argparse.ArgumentParser(description="Ingest documents into Qdrant via Ollama embeddings")
    parser.add_argument("--source", required=True, help="Source directory containing documents")
    parser.add_argument("--collection", required=True, help="Qdrant collection name")
    parser.add_argument("--ollama-url", default=os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434"))
    parser.add_argument("--qdrant-url", default=os.getenv("QDRANT_URL", "http://qdrant:6333"))
    parser.add_argument("--chunk-size", type=int, default=1000, help="Chunk size in characters")
    parser.add_argument("--chunk-overlap", type=int, default=200, help="Overlap in characters")
    parser.add_argument("--batch-size", type=int, default=32, help="Embedding batch size")
    return parser.parse_args()


def extract_pdf(path: Path) -> list[dict]:
    """Extract text from PDF, returning list of {text, page_num}."""
    pages = []
    doc = fitz.open(str(path))
    for i, page in enumerate(doc):
        text = page.get_text().strip()
        if text:
            pages.append({"text": text, "page_num": i + 1})
    doc.close()
    return pages


def extract_docx(path: Path) -> str:
    doc = Document(str(path))
    return "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())


def extract_doc(path: Path) -> str:
    try:
        result = subprocess.run(["antiword", str(path)], capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            return result.stdout.strip()
        return ""
    except Exception:
        return ""


def chunk_text(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    """Split text on paragraph boundaries targeting chunk_size with chunk_overlap."""
    paragraphs = text.split("\n\n")
    chunks = []
    current = ""
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        if current and len(current) + len(para) + 2 > chunk_size:
            chunks.append(current)
            # Keep overlap from end of current chunk
            if chunk_overlap > 0 and len(current) > chunk_overlap:
                current = current[-chunk_overlap:] + "\n\n" + para
            else:
                current = para
        else:
            current = current + "\n\n" + para if current else para
    if current.strip():
        chunks.append(current)
    return chunks


def make_point_id(collection: str, filename: str, chunk_index: int) -> str:
    raw = f"{collection}:{filename}:{chunk_index}"
    return str(uuid.UUID(hashlib.md5(raw.encode()).hexdigest()))


def embed_batch(texts: list[str], ollama_url: str) -> list[list[float]]:
    resp = httpx.post(
        f"{ollama_url}/api/embed",
        json={"model": "nomic-embed-text", "input": texts},
        timeout=120.0,
    )
    resp.raise_for_status()
    return resp.json()["embeddings"]


def find_documents(source_dir: str) -> list[Path]:
    docs = []
    for root, _, files in os.walk(source_dir):
        for f in files:
            if Path(f).suffix.lower() in SUPPORTED_EXTENSIONS:
                docs.append(Path(root) / f)
    return sorted(docs)


def main():
    args = parse_args()
    source = Path(args.source)
    if not source.is_dir():
        print(f"Error: source directory '{source}' does not exist", file=sys.stderr)
        sys.exit(1)

    qdrant = QdrantClient(url=args.qdrant_url, api_key=os.getenv("QDRANT_API_KEY") or None)

    # Create collection if not exists
    collections = [c.name for c in qdrant.get_collections().collections]
    if args.collection not in collections:
        qdrant.create_collection(
            collection_name=args.collection,
            vectors_config=VectorParams(size=768, distance=Distance.COSINE),
        )
        print(f"Created collection '{args.collection}'")
    else:
        print(f"Collection '{args.collection}' already exists")

    documents = find_documents(args.source)
    print(f"Found {len(documents)} documents in '{args.source}'")

    total_chunks = 0
    total_errors = 0
    files_processed = 0

    for doc_path in tqdm(documents, desc="Processing files"):
        try:
            ext = doc_path.suffix.lower()
            all_chunks = []

            if ext == ".pdf":
                pages = extract_pdf(doc_path)
                for page_info in pages:
                    chunks = chunk_text(page_info["text"], args.chunk_size, args.chunk_overlap)
                    for chunk in chunks:
                        all_chunks.append({
                            "text": chunk,
                            "page_num": page_info["page_num"],
                        })
            elif ext == ".docx":
                text = extract_docx(doc_path)
                if text:
                    chunks = chunk_text(text, args.chunk_size, args.chunk_overlap)
                    all_chunks = [{"text": c, "page_num": None} for c in chunks]
            elif ext in (".txt", ".md"):
                text = doc_path.read_text(encoding="utf-8", errors="replace").strip()
                if text:
                    chunks = chunk_text(text, args.chunk_size, args.chunk_overlap)
                    all_chunks = [{"text": c, "page_num": None} for c in chunks]
            elif ext == ".doc":
                text = extract_doc(doc_path)
                if text:
                    chunks = chunk_text(text, args.chunk_size, args.chunk_overlap)
                    all_chunks = [{"text": c, "page_num": None} for c in chunks]

            if not all_chunks:
                continue

            # Process in batches
            for i in range(0, len(all_chunks), args.batch_size):
                batch = all_chunks[i : i + args.batch_size]
                texts = [c["text"] for c in batch]
                embeddings = embed_batch(texts, args.ollama_url)

                points = []
                for j, (chunk_info, embedding) in enumerate(zip(batch, embeddings)):
                    chunk_idx = i + j
                    point_id = make_point_id(args.collection, doc_path.name, chunk_idx)
                    points.append(
                        PointStruct(
                            id=point_id,
                            vector=embedding,
                            payload={
                                "text": chunk_info["text"],
                                "filename": doc_path.name,
                                "page_num": chunk_info["page_num"],
                                "chunk_index": chunk_idx,
                                "source_dir": str(doc_path.parent),
                            },
                        )
                    )
                qdrant.upsert(collection_name=args.collection, points=points)
                total_chunks += len(points)

            files_processed += 1

        except Exception as e:
            tqdm.write(f"Warning: error processing {doc_path.name}: {e}")
            total_errors += 1

    print(f"\nSummary: {files_processed} files processed, {total_chunks} chunks created, {total_errors} errors")


if __name__ == "__main__":
    main()
