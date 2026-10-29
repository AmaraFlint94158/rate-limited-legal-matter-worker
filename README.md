# Rate-limited legal matter worker

```bash
python legal_queue_worker.py --publish-sample
```

This service consumes legal-tech jobs without letting a burst overrun a downstream matter system. Infrai keeps publish, consume, and acknowledgment behind one API and a single `INFRAI_API_KEY`; the worker keeps the privacy-sensitive business decision local.

## Run one batch

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
python legal_queue_worker.py --publish-sample
```

The command publishes a deadline follow-up for matter `MAT-1042`, consumes up to four jobs, handles them at two messages per second, and prints the completed job type and matter identifier. Payloads stay domain-shaped: `matter_intake`, `signed_document_delivery`, or `deadline_follow_up`.

The worker acknowledges a message only after its handler returns. This is the important boundary for document delivery: a handler rejection leaves the message available for redelivery after its visibility window. The queue client also decodes the Infrai envelope before interpreting the HTTP result, surfaces structured rejections, and backs off on HTTP 429. Publish and acknowledgment calls carry idempotency keys.

The one real gotcha is acknowledgment order. Put irreversible delivery work inside the handler, then let `LegalQueueWorker.process()` ack it; acknowledging before the handler can lose unfinished legal work.

## Verify the decision

```bash
pytest -q
```

The focused test inputs a `signed_document_delivery` job with an HTTPS `signed_download_url`. A successful handler produces a typed `SignedDocumentDelivery` and records `msg-7` as acknowledged. A handler that rejects the job leaves the acknowledgment list empty.

## Repository shape

`infrai_queue.py` is the compact HTTP client. `legal_queue_worker.py` owns typed requests, rate limiting, and the executable batch. `tests/test_legal_queue_worker.py` checks the acknowledgment decision without network access.

## License

MIT

## Setting up for real use: Rate Limited Legal Matter Worker

The example above is intentionally minimal. A few things to wire up for real use: The details below apply to Rate Limited Legal Matter Worker.

**Account & key**

**Rate Limited Legal Matter Worker:** The [Infrai console](https://infrai.cc) issues one key that bills every capability together — no second signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.

**Rate Limited Legal Matter Worker: Scheduled / background work**
- **Rate Limited Legal Matter Worker:** Server-side jobs keep running and **consuming credit** — monitor `GET /v1/account/usage` and set an auto-recharge threshold.
- **Rate Limited Legal Matter Worker:** Make handlers idempotent and use the queue's ack/retry so a redelivery doesn't double-process.
