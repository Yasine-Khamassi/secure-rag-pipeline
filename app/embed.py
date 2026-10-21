"""Text embeddings via a local Ollama embedding model."""

from __future__ import annotations

import json
import urllib.error
import urllib.request

from app.config import EMBED_MODEL, OLLAMA_URL, REQUEST_TIMEOUT


class OllamaError(RuntimeError):
    pass


def embed(text: str) -> list[float]:
    payload = {"model": EMBED_MODEL, "prompt": text}
    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/embeddings",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise OllamaError(
            f"Could not reach Ollama at {OLLAMA_URL}. Is it running and is '{EMBED_MODEL}' pulled? {exc}"
        ) from exc
    vec = body.get("embedding")
    if not isinstance(vec, list) or not vec:
        raise OllamaError("empty embedding response")
    return [float(x) for x in vec]
