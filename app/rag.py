"""
The Northwind RAG assistant: ingest -> embed -> role-aware retrieve -> answer.

Two modes:
- vulnerable: no entitlement filtering at retrieval, retrieved text spliced raw
  into the prompt.
- defended: retrieval filtered by the user's entitlements, retrieved chunks
  labelled as untrusted data, output passed through a DLP backstop.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field

from app.config import CHAT_MODEL, OLLAMA_URL, REQUEST_TIMEOUT, TEMPERATURE, TOP_K
from app.corpus import fresh_documents
from app.embed import embed, OllamaError
from app.store import VectorStore
from defenses.controls import (
    allowed_roles, build_context, validate_output, DEFENDED_SYSTEM, VULNERABLE_SYSTEM,
)


@dataclass
class Answer:
    text: str
    retrieved: list[dict] = field(default_factory=list)
    hr_dlp_redacted: bool = False


def build_index() -> VectorStore:
    store = VectorStore()
    for doc in fresh_documents():
        doc.vector = embed(doc.text)
        store.add(doc)
    return store


def _chat(system: str, user: str) -> str:
    payload = {
        "model": CHAT_MODEL,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "stream": False,
        "options": {"temperature": TEMPERATURE},
    }
    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise OllamaError(f"Could not reach Ollama at {OLLAMA_URL}: {exc}") from exc
    return (body.get("message") or {}).get("content", "")


def answer(store: VectorStore, query: str, user_role: str, defended: bool) -> Answer:
    qvec = embed(query)
    roles = allowed_roles(user_role) if defended else None
    hits = store.search(qvec, TOP_K, roles)
    retrieved = [{"id": r.id, "role": r.role, "source": r.source} for r, _ in hits]
    context = build_context([r.text for r, _ in hits], defended)
    system = DEFENDED_SYSTEM if defended else VULNERABLE_SYSTEM
    raw = _chat(system, f"CONTEXT:\n{context}\n\nQUESTION: {query}")
    if defended:
        text, redacted = validate_output(raw)
        return Answer(text=text, retrieved=retrieved, hr_dlp_redacted=redacted)
    return Answer(text=raw, retrieved=retrieved)
