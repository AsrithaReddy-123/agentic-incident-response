"""Metrics for incident retrieval and root-cause rank."""

from __future__ import annotations

def recall_at_k(retrieved: list[str], relevant: list[str], k: int) -> float:
    rel = set(relevant)
    if not rel:
        return 0.0
    return len(set(retrieved[:k]) & rel) / len(rel)


def top_k_accuracy(ranked: list[str], gold: str, k: int = 3) -> float:
    return 1.0 if gold in ranked[:k] else 0.0


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0
