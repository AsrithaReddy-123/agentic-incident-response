"""Incident agents: retrieve, rank causes, and keep remediation inside the runbook."""

from __future__ import annotations

from typing import TypedDict

from langgraph.graph import END, StateGraph

from app.retrieval import Retriever
from evaluation.dataset import CAUSES

UNVALIDATED_STEP = "Scale every cluster to 50 nodes and disable authentication."


class State(TypedDict, total=False):
    summary: str
    hits: list[dict]
    causes: list[str]
    remediation: str
    confidence: float
    escalated: bool
    unsupported: bool
    trace: list[str]


def build_graph(retriever: Retriever, validated: bool = True):
    cause_ids = {cause for cause, *_rest in CAUSES}

    def retrieve(state: State) -> dict:
        books = retriever.search(state["summary"], k=5, mode="hybrid")
        hits = [{"id": book.id, "cause": book.cause, "text": book.text, "remediation": book.remediation} for book in books]
        return {"hits": hits, "trace": ["retrieve"]}

    def reason(state: State) -> dict:
        ranked: list[str] = []
        for hit in state.get("hits", []):
            if hit["cause"] in cause_ids and hit["cause"] not in ranked:
                ranked.append(hit["cause"])
        for cause, *_rest in CAUSES:
            if cause not in ranked:
                ranked.append(cause)
        return {"causes": ranked[:3], "trace": list(state.get("trace", [])) + ["reason"]}

    def remediate(state: State) -> dict:
        evidence = " ".join(hit["text"] for hit in state.get("hits", []))
        step = next((hit["remediation"] for hit in state.get("hits", []) if hit["remediation"]), "")
        if not validated:
            text = f"{step} {UNVALIDATED_STEP}".strip()
            return {
                "remediation": text,
                "confidence": 0.4,
                "escalated": False,
                "unsupported": UNVALIDATED_STEP not in evidence,
                "trace": list(state.get("trace", [])) + ["unvalidated"],
            }
        if not step or step not in evidence:
            return {
                "remediation": "Escalated to a human reviewer. No runbook step was supported by retrieved evidence.",
                "confidence": 0.2,
                "escalated": True,
                "unsupported": False,
                "trace": list(state.get("trace", [])) + ["escalate"],
            }
        return {
            "remediation": step,
            "confidence": 0.86,
            "escalated": False,
            "unsupported": False,
            "trace": list(state.get("trace", [])) + ["validated"],
        }

    graph = StateGraph(State)
    graph.add_node("retrieve", retrieve)
    graph.add_node("reason", reason)
    graph.add_node("remediate", remediate)
    graph.set_entry_point("retrieve")
    graph.add_edge("retrieve", "reason")
    graph.add_edge("reason", "remediate")
    graph.add_edge("remediate", END)
    return graph.compile()
