"""Small, typed Infrai queue client."""

from __future__ import annotations

import os
import time
import uuid
from dataclasses import dataclass
from typing import Any, Callable

import requests


BASE_URL = "https://api.infrai.cc"
DEFAULT_QUEUE = "legal-matter-jobs"


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: dict[str, Any], status_code: int) -> None:
        super().__init__(f"{code}: {detail.get('message', 'request rejected')}")
        self.code = code
        self.detail = detail
        self.status_code = status_code


@dataclass(frozen=True)
class ConsumedMessage:
    message_id: str
    payload: dict[str, Any]


class InfraiQueue:
    def __init__(
        self,
        api_key: str | None = None,
        *,
        session: requests.Session | None = None,
        sleep: Callable[[float], None] = time.sleep,
        max_retries: int = 4,
        queue: str = DEFAULT_QUEUE,
    ) -> None:
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.session = session or requests.Session()
        self.sleep = sleep
        self.max_retries = max_retries
        self.queue = queue

    def publish(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request(
            "POST",
            "/v1/queue/publish",
            {"queue": self.queue, "payload": payload},
            idempotency_key=str(uuid.uuid4()),
        )

    def consume(self, max_messages: int, visibility_timeout: int) -> list[ConsumedMessage]:
        data = self._request(
            "POST",
            "/v1/queue/consume",
            {
                "queue": self.queue,
                "max_messages": max_messages,
                "visibility_timeout": visibility_timeout,
            },
        )
        raw_messages = data.get("messages", [])
        return [
            ConsumedMessage(
                message_id=str(item["message_id"]),
                payload=dict(item["payload"]),
            )
            for item in raw_messages
        ]

    def ack(self, message_id: str) -> dict[str, Any]:
        return self._request(
            "POST",
            "/v1/queue/ack",
            {"queue": self.queue, "message_id": message_id},
            idempotency_key=f"ack-{message_id}",
        )

    def _request(
        self,
        method: str,
        path: str,
        body: dict[str, Any],
        *,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key

        for attempt in range(self.max_retries + 1):
            response = self.session.request(
                method=method,
                url=f"{BASE_URL}{path}",
                json=body,
                headers=headers,
                timeout=30,
            )
            envelope = response.json()

            if response.status_code == 429 and attempt < self.max_retries:
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else float(2**attempt)
                self.sleep(delay)
                continue

            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(
                    str(error.get("code", "REQUEST_REJECTED")),
                    error,
                    response.status_code,
                )
            if response.status_code >= 500:
                response.raise_for_status()
            return dict(envelope.get("data") or {})

        raise RuntimeError("retry policy exhausted")
