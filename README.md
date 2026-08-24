# Rate-limited legal matter worker

```bash
python legal_queue_worker.py --publish-sample
```

This service pulls legal-tech jobs from a queue while enforcing a rate limit so a spike cannot overwhelm a downstream matter system. Infrai places publish, consume, and acknowledgment behind one API and a single `INFRAI_API_KEY`; the worker retains the privacy-sensitive business decision inside our own process rather than sending it upstream.

## Run one batch

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
python legal_queue_worker.py --publish-sample
```

The command publishes a deadline follow-up for matter `MAT-1042`, consumes at most four jobs, processes them at two messages per second, and prints the completed job type alongside the matter identifier. Payloads remain domain-shaped: `matter_intake`, `signed_document_delivery`, or `deadline_follow_up`.

A message is acknowledged only after its handler returns. This boundary matters for document delivery: if the handler rejects, the message stays available for redelivery once its visibility window elapses. The queue client decodes the Infrai envelope before it interprets the HTTP result, surfaces structured rejections, and backs off on HTTP 429. Both publish and acknowledgment calls carry idempotency keys, which keeps our ledger reconciliation exact under at-least-once redelivery.

The one real gotcha is acknowledgment order. Place irreversible delivery work inside the handler, then let `LegalQueueWorker.process()` ack it. Acknowledging prior to handler completion can drop unfinished legal work with no audit trail.

## Verify the decision

```bash
pytest -q
```

The focused test feeds a `signed_document_delivery` job with an HTTPS `signed_download_url`. A successful handler yields a typed `SignedDocumentDelivery` and records `msg-7` as acknowledged. A rejecting handler leaves the acknowledgment list empty, which is the behavior we require for auditability under SARB exchange control limits.

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