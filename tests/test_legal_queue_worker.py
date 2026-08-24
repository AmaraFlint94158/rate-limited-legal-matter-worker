from __future__ import annotations

import pytest

from infrai_queue import ConsumedMessage
from legal_queue_worker import LegalQueueWorker, SignedDocumentDelivery


class RecordingQueue:
    def __init__(self) -> None:
        self.acked: list[str] = []

    def ack(self, message_id: str) -> dict[str, bool]:
        self.acked.append(message_id)
        return {"acked": True}


def test_signed_delivery_is_acked_only_after_domain_handler_succeeds() -> None:
    queue = RecordingQueue()
    observed: list[SignedDocumentDelivery] = []
    worker = LegalQueueWorker(queue, observed.append)  # type: ignore[arg-type]
    message = ConsumedMessage(
        "msg-7",
        {
            "job_type": "signed_document_delivery",
            "matter_id": "MAT-1042",
            "signed_download_url": "https://documents.example/MAT-1042/signed",
        },
    )

    job = worker.process(message)

    assert job == SignedDocumentDelivery(
        "signed_document_delivery",
        "MAT-1042",
        "https://documents.example/MAT-1042/signed",
    )
    assert observed == [job]
    assert queue.acked == ["msg-7"]


def test_failed_delivery_is_left_unacked_for_redelivery() -> None:
    queue = RecordingQueue()

    def reject(_: object) -> None:
        raise ValueError("document policy rejected the delivery")

    worker = LegalQueueWorker(queue, reject)  # type: ignore[arg-type]
    message = ConsumedMessage(
        "msg-8",
        {
            "job_type": "signed_document_delivery",
            "matter_id": "MAT-1043",
            "signed_download_url": "https://documents.example/MAT-1043/signed",
        },
    )

    with pytest.raises(ValueError, match="document policy"):
        worker.process(message)

    assert queue.acked == []

