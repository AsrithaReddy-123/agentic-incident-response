"""Dense plus BM25 retrieval over runbooks."""

from __future__ import annotations

import numpy as np
from rank_bm25 import BM25Okapi

from app.tokenize import tokenize
from evaluation.dataset import Runbook


class HashEmbedder:
    def __init__(self, dim: int = 384) -> None:
        self.dim = dim
        self.model_name = "hash"

    def encode(self, texts: list[str]) -> np.ndarray:
        import hashlib

        matrix = np.zeros((len(texts), self.dim), dtype=np.float32)
        for row, text in enumerate(texts):
            for token in tokenize(text):
                digest = hashlib.md5(token.encode()).digest()
                matrix[row, int.from_bytes(digest[:4], "little") % self.dim] += 1 if digest[4] % 2 == 0 else -1
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return matrix / norms


class MiniLMEmbedder:
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2") -> None:
        from sentence_transformers import SentenceTransformer

        self.model_name = model_name
        self.model = SentenceTransformer(model_name)
        self.dim = int(self.model.get_sentence_embedding_dimension())

    def encode(self, texts: list[str]) -> np.ndarray:
        vectors = self.model.encode(texts, normalize_embeddings=True, batch_size=64, show_progress_bar=len(texts) > 256)
        return np.asarray(vectors, dtype=np.float32)


def load_embedder(name: str):
    if name == "hash":
        return HashEmbedder()
    return MiniLMEmbedder(name)


class Retriever:
    def __init__(self, runbooks: list[Runbook], embedder) -> None:
        self.runbooks = runbooks
        self.by_id = {book.id: book for book in runbooks}
        self.embedder = embedder
        self.bm25 = BM25Okapi([tokenize(book.text) for book in runbooks])
        self.matrix = embedder.encode([book.text for book in runbooks])

    def search(self, query: str, k: int = 5, mode: str = "hybrid") -> list[Runbook]:
        if mode == "vector":
            order = self._vector_order(query)
        elif mode == "bm25":
            order = self._bm25_order(query)
        else:
            fused: dict[str, float] = {}
            for rank, index in enumerate(self._vector_order(query)[:40]):
                fused[self.runbooks[index].id] = fused.get(self.runbooks[index].id, 0.0) + 1 / (60 + rank + 1)
            for rank, index in enumerate(self._bm25_order(query)[:40]):
                fused[self.runbooks[index].id] = fused.get(self.runbooks[index].id, 0.0) + 1 / (60 + rank + 1)
            ranked_ids = [doc_id for doc_id, _score in sorted(fused.items(), key=lambda item: item[1], reverse=True)]
            return [self.by_id[doc_id] for doc_id in ranked_ids[:k]]
        return [self.runbooks[index] for index in order[:k]]

    def _vector_order(self, query: str) -> list[int]:
        scores = self.matrix @ self.embedder.encode([query])[0]
        return [int(i) for i in np.argsort(-scores)]

    def _bm25_order(self, query: str) -> list[int]:
        scores = self.bm25.get_scores(tokenize(query))
        return [int(i) for i in np.argsort(-scores)]
