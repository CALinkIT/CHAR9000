import httpx
import psycopg2
from crewai.tools import tool
from config import N8N_WEBHOOK_BASE, QDRANT_URL, QDRANT_API_KEY, POSTGRES_URL


@tool("N8n Webhook Tool")
def n8n_webhook_tool(webhook_path: str, payload: dict) -> str:
    """Call an n8n webhook to trigger a workflow. Provide the webhook path and a JSON payload."""
    url = f"{N8N_WEBHOOK_BASE}/{webhook_path.lstrip('/')}"
    with httpx.Client(timeout=60) as client:
        resp = client.post(url, json=payload)
        resp.raise_for_status()
        return resp.text


@tool("Qdrant Search Tool")
def qdrant_search_tool(query: str, collection_name: str) -> str:
    """Search a Qdrant vector collection by query text. Returns matching documents."""
    from qdrant_client import QdrantClient

    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    results = client.query(collection_name=collection_name, query_text=query, limit=5)
    if not results:
        return "No results found."
    output = []
    for point in results:
        payload_text = point.metadata if hasattr(point, "metadata") else str(point)
        output.append(str(payload_text))
    return "\n---\n".join(output)


@tool("Database Query Tool")
def database_query_tool(query: str) -> str:
    """Run a read-only SELECT query against the PostgreSQL database. Only SELECT statements are allowed."""
    if not query.strip().upper().startswith("SELECT"):
        return "Error: Only SELECT queries are allowed."
    conn = psycopg2.connect(POSTGRES_URL)
    try:
        conn.set_session(readonly=True)
        cur = conn.cursor()
        cur.execute(query)
        columns = [desc[0] for desc in cur.description] if cur.description else []
        rows = cur.fetchmany(100)
        if not rows:
            return "Query returned no results."
        header = " | ".join(columns)
        lines = [header, "-" * len(header)]
        for row in rows:
            lines.append(" | ".join(str(v) for v in row))
        return "\n".join(lines)
    finally:
        conn.close()
