"""Token helpers for incident retrieval."""

from __future__ import annotations

import re

_TOKEN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
STOP = frozenset({"a", "an", "the", "and", "or", "of", "to", "in", "on", "for", "with", "is", "are"})


def tokenize(text: str) -> list[str]:
    tokens = [tok for tok in _TOKEN.findall(text.lower()) if tok not in STOP and len(tok) > 1]
    return tokens or ["blank"]
