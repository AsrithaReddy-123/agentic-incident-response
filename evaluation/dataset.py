"""Synthetic services, labeled incidents, runbooks, and log events."""

from __future__ import annotations

import random
from dataclasses import dataclass

CAUSES = [
    ("ledger_replica_lag", "Ledger", "PX-4419", "Treasury Platform", "Fail over the ledger replica to the secondary site and confirm lag is under 2 seconds."),
    ("pool_exhausted", "Checkout", "PX-2201", "Commerce Experience", "Raise the checkout connection pool and drain idle sessions older than 60 seconds."),
    ("token_clock_skew", "Identity", "PX-1180", "Security Engineering", "Resync the identity host clock and reissue tokens minted during the skew window."),
    ("disk_watermark", "Catalog", "PX-9033", "Retail Platform", "Expand the catalog volume and delete debug snapshots older than one day."),
    ("bad_deploy", "Billing", "PX-5512", "Revenue Systems", "Roll billing back to the previous release and pause the invoice worker."),
    ("queue_backlog", "Notifications", "PX-3304", "Messaging Platform", "Scale notification consumers and replay the dead-letter topic from the last checkpoint."),
    ("cache_stampede", "Search", "PX-7720", "Discovery Platform", "Enable search request coalescing and warm the query cache before reopening traffic."),
    ("lock_contention", "Inventory", "PX-2844", "Supply Chain", "Shorten inventory row locks and retry the reservation with jitter."),
    ("dns_ttl", "Shipping", "PX-6408", "Logistics", "Lower the shipping DNS TTL and flush the local resolver cache."),
    ("cert_expiry", "Gateway", "PX-1019", "Security Engineering", "Install the renewed gateway certificate and reload the edge process."),
]


@dataclass
class Runbook:
    id: str
    cause: str
    service: str
    code: str
    team: str
    text: str
    remediation: str


@dataclass
class Incident:
    id: str
    cause: str
    service: str
    code: str
    summary: str
    gold_ids: list[str]


def build_runbooks() -> list[Runbook]:
    books = []
    for index in range(5200):
        cause, service, code, team, step = CAUSES[index % len(CAUSES)]
        if index < len(CAUSES):
            doc_id = f"rb-{cause}"
            text = (
                f"Runbook {doc_id}: alert {code} on {service} indicates {cause.replace('_', ' ')}. "
                f"Owning team: {team}. Remediation: {step}"
            )
        else:
            doc_id = f"note-{index}"
            text = (
                f"Historical note {doc_id}: operators discussed office capacity, cafeteria wifi, "
                f"and a status-page typo. No customer impact was declared."
            )
            cause, service, code, team, step = "none", service, "", "", ""
        books.append(Runbook(doc_id, cause, service, code, team, text, step if index < len(CAUSES) else ""))
    return books


def build_incidents(n: int = 80, seed: int = 7) -> list[Incident]:
    rng = random.Random(seed)
    incidents = []
    for index in range(n):
        cause, service, code, _team, _step = CAUSES[index % len(CAUSES)]
        incidents.append(
            Incident(
                id=f"INC-{1000 + index}",
                cause=cause,
                service=service,
                code=code,
                summary=f"Customer errors rose on {service}. Dominant signal is alert {code}.",
                gold_ids=[f"rb-{cause}"],
            )
        )
    rng.shuffle(incidents)
    return incidents


def generate_logs(n: int = 100_000, seed: int = 7):
    rng = random.Random(seed)
    services = [row[1] for row in CAUSES]
    for index in range(n):
        cause, service, code, _team, _step = CAUSES[index % len(CAUSES)]
        level = "ERROR" if index % 50 == 0 else rng.choice(["INFO", "WARN", "INFO", "INFO"])
        message = f"{code} {cause.replace('_', ' ')}" if level == "ERROR" else f"{service} request ok"
        yield {
            "id": index,
            "service": service if level == "ERROR" else rng.choice(services),
            "level": level,
            "message": message,
            "code": code if level == "ERROR" else "",
        }
