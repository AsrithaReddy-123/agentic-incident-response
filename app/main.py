"""FastAPI incident investigation API."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from pydantic import BaseModel

from app.agents import build_graph
from app.retrieval import Retriever, load_embedder
from app.streaming import build_bus
from evaluation.dataset import build_runbooks


class InvestigateRequest(BaseModel):
    summary: str


def create_app(embedder_name: str | None = None) -> FastAPI:
    name = embedder_name or os.getenv("EMBEDDER", "sentence-transformers/all-MiniLM-L6-v2")

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        books = build_runbooks()
        app.state.retriever = Retriever(books, load_embedder(name))
        app.state.graph = build_graph(app.state.retriever, validated=True)
        app.state.bus = build_bus(os.getenv("KAFKA_BOOTSTRAP"))
        app.state.stats = {"investigations": 0, "escalations": 0}
        yield

    app = FastAPI(title="Agentic Incident Response", version="0.1.0", lifespan=lifespan)

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.post("/investigate")
    def investigate(body: InvestigateRequest) -> dict:
        result = app.state.graph.invoke({"summary": body.summary, "trace": []})
        app.state.stats["investigations"] += 1
        if result.get("escalated"):
            app.state.stats["escalations"] += 1
        return {
            "causes": result.get("causes", []),
            "remediation": result.get("remediation", ""),
            "confidence": result.get("confidence", 0.0),
            "escalated": result.get("escalated", False),
            "citations": [hit["id"] for hit in result.get("hits", [])],
            "trace": result.get("trace", []),
        }

    @app.get("/stats")
    def stats() -> dict:
        return app.state.stats

    return app


app = create_app()
