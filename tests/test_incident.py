from fastapi.testclient import TestClient

from app.main import create_app
from evaluation.dataset import build_incidents, generate_logs
from evaluation.metrics import recall_at_k


def test_log_stream_exceeds_one_thousand_per_second():
    from app.indexing import LocalIndex
    from app.streaming import InProcessBus
    from evaluation.dataset import build_runbooks

    bus = InProcessBus()
    index = LocalIndex(build_runbooks())
    import time

    started = time.perf_counter()
    n = 20000
    for event in generate_logs(n):
        bus.publish("logs", event)
        index.add_log(event)
    rate = n / (time.perf_counter() - started)
    assert rate > 1000


def test_labeled_incident_retrieves_runbook():
    from app.retrieval import Retriever, load_embedder
    from evaluation.dataset import build_runbooks

    incident = build_incidents(1, seed=1)[0]
    retriever = Retriever(build_runbooks(), load_embedder("hash"))
    hits = retriever.search(incident.summary, k=5, mode="bm25")
    assert recall_at_k([hit.id for hit in hits], incident.gold_ids, 5) == 1.0


def test_health():
    app = create_app("hash")
    with TestClient(app) as client:
        assert client.get("/health").json()["status"] == "ok"
        body = client.post("/investigate", json={"summary": "Customer errors rose on Ledger. Dominant signal is alert PX-4419."}).json()
        assert "remediation" in body
        assert body["causes"]
