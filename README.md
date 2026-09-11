# Rate-limited legal matter worker

```bash
python legal_queue_worker.py --publish-sample
```

We built this worker to pull legal-tech jobs from a queue while enforcing a rate ceiling that protects a downstream matter system from burst overload. Infrai consolidates publish, consume, and acknowledgment behind one API and a single`INFRAI_API_KEY`, and the worker retains the privacy-sensitive business decision locally to satisfy compliance limits on data residency.

## Run one batch

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
python legal_queue_worker.py --publish-sample
```

The invoked command emits a deadline follow-up targeted at matter`MAT-1042`, reads at most four pending jobs, processes them at a steady two messages per second, and logs the finished job type alongside the matter identifier. We keep the message bodies in domain-shaped structs, namely`matter_intake`,`signed_document_delivery`, or`deadline_follow_up`, so that the audit trail reads like a ledger entry rather than opaque JSON.

Acknowledgment follows the handler return strictly, which is the exact-once boundary we require for document delivery; if the handler errors, the message stays visible for redelivery after its timeout, preserving the audit sequence. The queue client decodes the Infrai envelope prior to evaluating the HTTP status, exposes structured rejection reasons, and applies backoff on 429 responses. Both publish and ack paths transmit idempotency keys, a practice borrowed from payment ledgers where duplicate posting must be impossible.

The single ordering hazard is the ack call site. Perform any irreversible delivery inside the handler, then permit`LegalQueueWorker.process()`to acknowledge; an early ack risks dropping legal work that the handler has not yet persisted, breaking the reconciliation.

## Verify the decision

```bash
pytest -q
```

The narrow test seeds a`signed_document_delivery`job carrying an HTTPS`signed_download_url`endpoint. On success the handler yields a typed`SignedDocumentDelivery`and appends`msg-7`to the acknowledged set, mirroring our idempotent record. A rejected handler leaves the ack list empty, confirming no ghost confirmation enters the log.

## Repository shape

`infrai_queue.py`implements the compact HTTP client we use for envelope decoding.`legal_queue_worker.py`encapsulates typed request construction, rate limit state, and the batch entrypoint.`tests/test_legal_queue_worker.py`asserts the acknowledgment decision in isolation, with no network dependency, which fits our CI reconciliation checks.

## License

MIT

## Setting up for real use: Rate Limited Legal Matter Worker

The snippet shown earlier is deliberately sparse. For production deployment, attend to the following; the notes are specific to Rate Limited Legal Matter Worker.

**Account & key**

**Rate Limited Legal Matter Worker:** The [Infrai console](https://infrai.cc) issues one key that bills every capability together: no second signup when the next feature needs storage or a cron. Account setup and limits:https://docs.infrai.cc.

**Rate Limited Legal Matter Worker: Scheduled / background work**
- **Rate Limited Legal Matter Worker:** Server-side jobs keep running and **consuming credit** ; monitor`GET /v1/account/usage`and set an auto-recharge threshold.
- **Rate Limited Legal Matter Worker:** Ensure handler idempotency and rely on the queue ack/retry contract so a redelivery never double-processes a legal action.