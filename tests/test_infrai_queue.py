from __future__ import annotations

from typing import Any

from infrai_queue import InfraiQueue


class Response:
    status_code = 200
    headers: dict[str, str] = {}

    def json(self) -> dict[str, Any]:
        return {"ok": True, "data": {"messages": []}}


class RecordingSession:
    def __init__(self) -> None:
        self.bodies: list[dict[str, Any]] = []

    def request(self, **kwargs: Any) -> Response:
        self.bodies.append(kwargs["json"])
        return Response()


def test_queue_operations_include_required_queue() -> None:
    session = RecordingSession()
    queue = InfraiQueue(api_key="test", session=session, queue="legal-test")  # type: ignore[arg-type]

    queue.publish({"job_type": "matter_intake"})
    queue.consume(4, 60)
    queue.ack("msg-7")

    assert session.bodies == [
        {"queue": "legal-test", "payload": {"job_type": "matter_intake"}},
        {"queue": "legal-test", "max_messages": 4, "visibility_timeout": 60},
        {"queue": "legal-test", "message_id": "msg-7"},
    ]
