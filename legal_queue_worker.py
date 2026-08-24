"""Rate-limited worker for privacy-sensitive legal matter operations."""

from __future__ import annotations

import argparse
import time
from dataclasses import dataclass
from typing import Any, Callable, Literal, Mapping

from infrai_queue import ConsumedMessage, InfraiQueue


@dataclass(frozen=True)
class MatterIntake:
    job_type: Literal["matter_intake"]
    matter_id: str
    client_reference: str


@dataclass(frozen=True)
class SignedDocumentDelivery:
    job_type: Literal["signed_document_delivery"]
    matter_id: str
    signed_download_url: str


@dataclass(frozen=True)
class DeadlineFollowUp:
    job_type: Literal["deadline_follow_up"]
    matter_id: str
    due_date: str


LegalJob = MatterIntake | SignedDocumentDelivery | DeadlineFollowUp


def parse_job(payload: Mapping[str, Any]) -> LegalJob:
    job_type = payload.get("job_type")
    if job_type == "matter_intake":
        return MatterIntake(job_type, str(payload["matter_id"]), str(payload["client_reference"]))
    if job_type == "signed_document_delivery":
        download_url = str(payload.get("signed_download_url", ""))
        if not download_url.startswith("https://"):
            raise ValueError("signed document delivery requires an HTTPS download URL")
        return SignedDocumentDelivery(job_type, str(payload["matter_id"]), download_url)
    if job_type == "deadline_follow_up":
        return DeadlineFollowUp(job_type, str(payload["matter_id"]), str(payload["due_date"]))
    raise ValueError("unknown legal job type")


class LegalQueueWorker:
    def __init__(
        self,
        queue: InfraiQueue,
        handler: Callable[[LegalJob], None],
        *,
        messages_per_second: float = 2.0,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if messages_per_second <= 0:
            raise ValueError("messages_per_second must be positive")
        self.queue = queue
        self.handler = handler
        self.interval = 1.0 / messages_per_second
        self.clock = clock
        self.sleep = sleep
        self.next_slot = 0.0

    def process(self, message: ConsumedMessage) -> LegalJob:
        now = self.clock()
        if now < self.next_slot:
            self.sleep(self.next_slot - now)
            now = self.clock()
        job = parse_job(message.payload)
        self.handler(job)
        self.queue.ack(message.message_id)
        self.next_slot = max(now, self.next_slot) + self.interval
        return job

    def run_once(self, max_messages: int = 4, visibility_timeout: int = 60) -> int:
        messages = self.queue.consume(max_messages, visibility_timeout)
        for message in messages:
            self.process(message)
        return len(messages)


def log_completed(job: LegalJob) -> None:
    print(f"completed {job.job_type} for matter {job.matter_id}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run one legal queue worker batch")
    parser.add_argument("--publish-sample", action="store_true")
    args = parser.parse_args()
    queue = InfraiQueue()
    if args.publish_sample:
        InfraiQueue().publish(
            {
                "job_type": "deadline_follow_up",
                "matter_id": "MAT-1042",
                "due_date": "2026-09-01",
            }
        )
    processed = LegalQueueWorker(queue, log_completed).run_once()
    print(f"processed {processed} job(s)")


if __name__ == "__main__":
    main()

