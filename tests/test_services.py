import json
import os
import time

import pytest


def test_kafka_publish_and_read():
    bootstrap = os.getenv("KAFKA_BOOTSTRAP", "").strip()
    if not bootstrap:
        pytest.skip("KAFKA_BOOTSTRAP is not set")
    from kafka import KafkaConsumer, KafkaProducer

    payload = {"id": 1, "service": "Ledger", "code": "PX-4419", "message": "replica lag"}
    producer = KafkaProducer(
        bootstrap_servers=bootstrap,
        value_serializer=lambda value: json.dumps(value).encode(),
    )
    producer.send("logs", payload)
    producer.flush()
    producer.close()
    consumer = KafkaConsumer(
        "logs",
        bootstrap_servers=bootstrap,
        auto_offset_reset="earliest",
        consumer_timeout_ms=20000,
        value_deserializer=lambda raw: json.loads(raw.decode()),
    )
    found = None
    deadline = time.time() + 20
    for message in consumer:
        if message.value.get("code") == "PX-4419":
            found = message.value
            break
        if time.time() > deadline:
            break
    consumer.close()
    assert found is not None
    assert found["service"] == "Ledger"


def test_elasticsearch_indexes_runbook():
    url = os.getenv("ELASTICSEARCH_URL", "").strip()
    if not url:
        pytest.skip("ELASTICSEARCH_URL is not set")
    from app.indexing import ElasticsearchIndex
    from evaluation.dataset import Runbook

    index = ElasticsearchIndex(url, index="runbooks-ci")
    index.setup()
    book = Runbook(
        id="rb-ledger_replica_lag",
        cause="ledger_replica_lag",
        service="Ledger",
        code="PX-4419",
        team="Treasury Platform",
        text="Runbook rb-ledger_replica_lag: alert PX-4419 on Ledger indicates ledger replica lag.",
        remediation="Fail over the ledger replica.",
    )
    index.bulk_runbooks([book])
    index.client.indices.refresh(index=index.index)
    ids = index.search_ids("alert PX-4419 Ledger", k=5)
    assert "rb-ledger_replica_lag" in ids
