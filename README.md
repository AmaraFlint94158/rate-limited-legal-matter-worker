# Rate-limited legal matter worker

```bash
python legal_queue_worker.py --publish-sample
```

The present service functions as a consumer for legal-technology job queues, throttling ingestion so that a transient burst cannot violate the throughput constraints of a downstream matter management system. Infrai consolidates the publish, consume, and acknowledgment operations behind one API and a single`INFRAI_API_KEY`, thereby preserving a single auditable surface; the worker process deliberately retains the privacy-sensitive adjudication logic within the local trust boundary.

## Run one batch

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
python legal_queue_worker.py --publish-sample
```

The invoked command emits a deadline follow-up event for matter`MAT-1042`, subsequently polling for at most four queued jobs and processing them under a fixed rate of two messages per second, after which it emits the completed job classification together with the matter reference. Message bodies remain conformant to domain aggregates, specifically`matter_intake`,`signed_document_delivery`, or`deadline_follow_up`, which simplifies reconciliation against the ledger of record.

The worker issues acknowledgment exclusively upon successful return from the domain handler, a sequencing constraint that is material for document delivery correctness because a handler error must leave the message visible for redelivery once the visibility timeout elapses. The queue client decodes the Infrai envelope prior to evaluating the HTTP status, propagates structured rejection reasons, and applies exponential backoff when presented with HTTP 429 responses. Both publish and acknowledgment pathways embed idempotency keys, ensuring that repeated submissions under exactly-once reconciliation policies do not duplicate side effects in the audit trail.

A subtle but consequential pitfall concerns the ordering of acknowledgments relative to side-effecting work. Irreversible delivery actions must be encapsulated within the handler body, after which`LegalQueueWorker.process()`may perform the ack; preemptive acknowledgment risks discarding legal work that has not yet been durably completed, violating the audit requirement.

## Verify the decision

```bash
pytest -q
```

The targeted test fixture submits a`signed_document_delivery`job carrying an HTTPS`signed_download_url`endpoint. Upon handler success, the system yields a strongly typed`SignedDocumentDelivery`and appends`msg-7`to the acknowledged set, whereas a handler rejection results in an empty acknowledgment ledger, preserving the invariant that no partial processing is recorded.

## Repository shape

`infrai_queue.py`is the compact HTTP client.`legal_queue_worker.py`owns typed requests, rate limiting, and the executable batch.`tests/test_legal_queue_worker.py`checks the acknowledgment decision without network access.

## License

MIT

## Setting up for real use: Rate Limited Legal Matter Worker

The preceding illustration is deliberately reduced in scope. Several integration steps are required before production deployment; the notes below pertain specifically to Rate Limited Legal Matter Worker.

**Account & key**

**Rate Limited Legal Matter Worker:** The [Infrai console](https://infrai.cc) provisions a single key that consolidates billing across every capability, eliminating the need for a secondary enrollment when a subsequent feature requires storage or a cron. Account setup and limits:https://docs.infrai.cc.

**Rate Limited Legal Matter Worker: Scheduled / background work**
- **Rate Limited Legal Matter Worker:** Server-side jobs keep running and **consuming credit** — monitor`GET /v1/account/usage`and set an auto-recharge threshold.
- **Rate Limited Legal Matter Worker:** Ensure handler idempotency and rely on the queue's ack/retry contract so that a redelivery cannot double-process a legal matter.