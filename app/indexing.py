"""Local inverted index and an optional Elasticsearch backend."""

from __future__ import annotations

from collections import defaultdict

from app.tokenize import tokenize
from evaluation.dataset import Runbook


class LocalIndex:
    def __init__(self, runbooks: list[Runbook]) -> None:
        self.docs = {book.id: book for book in runbooks}
        self.inverted: dict[str, set[str]] = defaultdict(set)
        for book in runbooks:
            for token in set(tokenize(book.text)):
                self.inverted[token].add(book.id)

    def add_log(self, event: dict) -> None:
        for token in set(tokenize(f"{event.get('service','')} {event.get('message','')} {event.get('code','')}")):
            self.inverted[token].add(f"log-{event['id']}")

    def search_ids(self, query: str, k: int = 5) -> list[str]:
        scores: dict[str, int] = defaultdict(int)
        for token in tokenize(query):
            for doc_id in self.inverted.get(token, ()):
                if doc_id.startswith("rb-") or doc_id.startswith("note-"):
                    scores[doc_id] += 1
        ranked = sorted(scores, key=lambda doc_id: scores[doc_id], reverse=True)
        return ranked[:k]


class ElasticsearchIndex:
    def __init__(self, url: str, index: str = "runbooks") -> None:
        from elasticsearch import Elasticsearch

        self.client = Elasticsearch(url)
        self.index = index

    def setup(self) -> None:
        if not self.client.indices.exists(index=self.index):
            self.client.indices.create(index=self.index)

    def bulk_runbooks(self, runbooks: list[Runbook]) -> None:
        from elasticsearch.helpers import bulk

        actions = (
            {"_index": self.index, "_id": book.id, "_source": {"text": book.text, "cause": book.cause}}
            for book in runbooks
        )
        bulk(self.client, actions)

    def search_ids(self, query: str, k: int = 5) -> list[str]:
        response = self.client.search(index=self.index, size=k, query={"match": {"text": query}})
        return [hit["_id"] for hit in response["hits"]["hits"]]
