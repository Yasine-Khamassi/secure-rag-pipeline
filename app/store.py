"""
A tiny in-memory vector store with cosine similarity and role-aware retrieval.

This is intentionally small and dependency-free so the whole lab runs on Node/
Python alone. It is a faithful stand-in for a production vector DB such as Chroma;
the security-relevant behaviour - metadata-filtered retrieval - is identical.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass
class Record:
    id: str
    role: str          # sensitivity/role required to see this document
    source: str        # 'internal' (trusted) or 'upload' (untrusted)
    text: str
    vector: list[float] = field(default_factory=list)


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return 0.0 if na == 0 or nb == 0 else dot / (na * nb)


class VectorStore:
    def __init__(self) -> None:
        self._records: list[Record] = []

    def add(self, record: Record) -> None:
        self._records.append(record)

    def search(self, query_vec: list[float], k: int, allowed_roles: set[str] | None) -> list[tuple[Record, float]]:
        """Top-k by cosine. If allowed_roles is given, documents whose role is not
        in it are filtered out BEFORE ranking (the access-control boundary). If it
        is None, no filtering happens - the vulnerable behaviour."""
        candidates = self._records
        if allowed_roles is not None:
            candidates = [r for r in candidates if r.role in allowed_roles]
        scored = [(r, _cosine(query_vec, r.vector)) for r in candidates]
        scored.sort(key=lambda t: t[1], reverse=True)
        return scored[:k]

    def __len__(self) -> int:
        return len(self._records)
