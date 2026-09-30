"""In-process bus used by the benchmark, plus a Kafka publisher when a broker is configured."""

from __future__ import annotations

import json


class InProcessBus:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    def publish(self, topic: str, event: dict) -> None:
        self.events.append((topic, event))


class KafkaBus:
    def __init__(self, bootstrap: str) -> None:
        from kafka import KafkaProducer

        self.producer = KafkaProducer(
            bootstrap_servers=bootstrap,
            value_serializer=lambda value: json.dumps(value).encode(),
        )

    def publish(self, topic: str, event: dict) -> None:
        self.producer.send(topic, event)

    def flush(self) -> None:
        self.producer.flush()


def build_bus(bootstrap: str | None) -> InProcessBus | KafkaBus:
    if bootstrap:
        return KafkaBus(bootstrap)
    return InProcessBus()
