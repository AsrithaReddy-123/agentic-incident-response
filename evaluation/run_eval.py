"""Benchmark ingestion throughput, Recall@5, and validated vs unvalidated remediation."""

from __future__ import annotations

import json
import time
from pathlib import Path

from app.agents import UNVALIDATED_STEP, build_graph
from app.indexing import LocalIndex
from app.retrieval import Retriever, load_embedder
from app.streaming import InProcessBus
from evaluation.dataset import build_incidents, build_runbooks, generate_logs
from evaluation.metrics import mean, recall_at_k, top_k_accuracy


def main() -> None:
    runbooks = build_runbooks()
    incidents = build_incidents(80)
    index = LocalIndex(runbooks)
    bus = InProcessBus()
    started = time.perf_counter()
    count = 0
    for event in generate_logs(100_000):
        bus.publish("logs", event)
        index.add_log(event)
        count += 1
    elapsed = time.perf_counter() - started
    rate = count / elapsed

    embedder_name = "sentence-transformers/all-MiniLM-L6-v2"
    retriever = Retriever(runbooks, load_embedder(embedder_name))
    recalls = []
    for incident in incidents:
        hits = retriever.search(incident.summary, k=5, mode="hybrid")
        recalls.append(recall_at_k([hit.id for hit in hits], incident.gold_ids, 5))

    validated = build_graph(retriever, validated=True)
    unvalidated = build_graph(retriever, validated=False)
    top3 = []
    bad_validated = 0
    bad_unvalidated = 0
    for incident in incidents:
        good = validated.invoke({"summary": incident.summary, "trace": []})
        raw = unvalidated.invoke({"summary": incident.summary, "trace": []})
        top3.append(top_k_accuracy(good.get("causes", []), incident.cause, 3))
        if good.get("unsupported"):
            bad_validated += 1
        if raw.get("unsupported") or UNVALIDATED_STEP in raw.get("remediation", ""):
            bad_unvalidated += 1
    n = len(incidents)
    payload = {
        "project": "agentic-incident-response",
        "log_events": count,
        "events_per_second": round(rate, 1),
        "runbook_chunks": len(runbooks),
        "labeled_incidents": n,
        "embedder": retriever.embedder.model_name,
        "recall@5": round(mean(recalls), 4),
        "top3_root_cause_accuracy": round(mean(top3), 4),
        "unsupported_rate_unvalidated": round(bad_unvalidated / n, 4),
        "unsupported_rate_validated": round(bad_validated / n, 4),
        "notes": "Synthetic logs and runbooks. Elasticsearch and Kafka clients are used when ELASTICSEARCH_URL or KAFKA_BOOTSTRAP is set. This run used the local index and in-process bus.",
    }
    if payload["unsupported_rate_unvalidated"]:
        payload["unsupported_reduction"] = round(
            1 - payload["unsupported_rate_validated"] / payload["unsupported_rate_unvalidated"], 4
        )
    out = Path("evaluation/results/benchmark.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2) + "\n")
    print(out.read_text())


if __name__ == "__main__":
    main()
