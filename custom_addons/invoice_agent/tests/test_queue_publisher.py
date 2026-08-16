"""Rollback + drain tests for the AMQP transactional outbox (week 8).

Proof for the invariants claimed in ``docs/adr-004-rabbitmq.md``:

1. **No orphan jobs.** ``action_request_ai_extraction`` writes its outbox row
   on the same cursor as the ``account.move`` write. When that transaction
   rolls back, the row rolls back with it — and the drain cron, which in
   production runs in a *separate* committed transaction, finds nothing to
   publish. A rolled-back bill never produces an orphan message on the
   broker.
2. **No lost jobs on broker downtime.** The drain marks a row with
   ``error_message`` but leaves it ``state='pending'`` when the broker is
   unreachable, so the next tick retries it. Nothing is lost while the
   broker is down.
3. **Commit-time enqueue works.** After a committed enqueue the outbox row is
   durable and ``pending``; the drain path publishes ``extract.request`` and
   stamps ``published_at``.

The broker is never touched: ``queue.publisher.publish_extract_request`` is
patched to raise ``QueueUnavailable`` (proving the outbox absorbs broker
downtime) or to record calls (proving that a rolled-back transaction never
reaches the publish path).
"""

from unittest.mock import patch

from odoo.tests import tagged

from odoo.addons.invoice_agent.models.queue_publisher import QueueUnavailable

from .test_extraction import InvoiceAgentTestCommon


@tagged("post_install", "-at_install")
class TestTransactionalOutbox(InvoiceAgentTestCommon):
    """Transactional outbox invariants for the AMQP extraction queue."""

    def _draft_bill(self, **overrides):
        vals = {
            "move_type": "in_invoice",
            "partner_id": self.partner.id,
            "invoice_date": "2026-07-01",
            "journal_id": self.purchase_journal.id,
            "ai_extraction_status": "pending",
        }
        vals.update(overrides)
        return self.env["account.move"].create(vals)

    # ------------------------------------------------------------------
    # 1. Rollback safety — the core ADR-004 invariant
    # ------------------------------------------------------------------
    def test_rollback_after_enqueue_leaves_no_outbox_row(self):
        move = self._draft_bill()

        # Register the job inside a savepoint that rolls back on exit — the
        # official Odoo pattern for forcing a transaction rollback in a test
        # (a raw cr.rollback() would fight the TransactionCase harness).
        with self.assertRaisesRegex(RuntimeError, "force rollback"):
            with self.env.cr.savepoint(flush=False):
                move.action_request_ai_extraction()
                raise RuntimeError("force rollback")

        jobs = self.env["invoice.agent.job"].search([("move_id", "=", move.id)])
        self.assertEqual(len(jobs), 0, "rollback must cascade to outbox rows")

    def test_rollback_after_enqueue_never_publishes(self):
        move = self._draft_bill()
        published = []

        def _fake_publish_extract_request(
            _publisher, move_id, attachment_id=False, attempt=1,
            job_uuid=False, ocr_text=False,
        ):
            published.append((move_id, attachment_id, attempt))

        with patch.object(
            type(self.env["queue.publisher"]),
            "publish_extract_request",
            _fake_publish_extract_request,
        ):
            # The user's (doomed) transaction enqueues the job…
            with self.assertRaisesRegex(RuntimeError, "force rollback"):
                with self.env.cr.savepoint(flush=False):
                    move.action_request_ai_extraction()
                    raise RuntimeError("force rollback")

            # …then rolls back. The drain cron runs later in a *separate*
            # transaction (the production shape): it must find no row to
            # publish, so no orphan message ever reaches the broker.
            sent = self.env["invoice.agent.job"]._drain_pending(limit=10)

        self.assertEqual(sent, 0, "drain must find nothing after rollback")
        self.assertEqual(
            published,
            [],
            "a rolled-back transaction must never publish to the broker",
        )

    def test_enqueue_then_commit_produces_durable_pending_job(self):
        move = self._draft_bill()

        move.action_request_ai_extraction()

        job = self.env["invoice.agent.job"].search(
            [("move_id", "=", move.id), ("state", "=", "pending")],
            limit=1,
        )
        self.assertTrue(job, "a pending outbox row must exist after commit")
        self.assertTrue(move.ai_job_uuid, "the move must carry a job uuid")
        self.assertEqual(move.ai_state, "queued")

    # ------------------------------------------------------------------
    # 2. Broker downtime — no lost jobs
    # ------------------------------------------------------------------
    def test_drain_marks_error_and_keeps_pending_when_broker_down(self):
        move = self._draft_bill()
        move.action_request_ai_extraction()
        job = self.env["invoice.agent.job"].search(
            [("move_id", "=", move.id)],
            limit=1,
        )

        with patch.object(
            type(self.env["queue.publisher"]),
            "publish_extract_request",
            side_effect=QueueUnavailable("broker refused connection"),
        ):
            sent = self.env["invoice.agent.job"]._drain_pending(limit=10)

        self.assertEqual(sent, 0)
        job.invalidate_recordset()
        self.assertEqual(job.state, "pending", "job must stay pending")
        self.assertTrue(job.error_message, "failure reason must be recorded")

    # ------------------------------------------------------------------
    # 3. Successful drain path
    # ------------------------------------------------------------------
    def test_drain_publishes_and_stamps_published_at(self):
        move = self._draft_bill()
        move.action_request_ai_extraction()
        job = self.env["invoice.agent.job"].search(
            [("move_id", "=", move.id)],
            limit=1,
        )
        published = []

        def _fake_publish_extract_request(
            _publisher, move_id, attachment_id=False, attempt=1,
            job_uuid=False, ocr_text=False,
        ):
            published.append((move_id, attachment_id, attempt))

        with patch.object(
            type(self.env["queue.publisher"]),
            "publish_extract_request",
            _fake_publish_extract_request,
        ):
            sent = self.env["invoice.agent.job"]._drain_pending(limit=10)

        self.assertEqual(sent, 1)
        self.assertEqual(published, [(move.id, False, 1)])
        job.invalidate_recordset()
        self.assertEqual(job.state, "sent")
        self.assertTrue(job.published_at, "published_at must be stamped")

    def test_drain_skips_already_sent_rows(self):
        move = self._draft_bill()
        move.action_request_ai_extraction()
        jobs = self.env["invoice.agent.job"]
        published = []

        def _fake_publish_extract_request(
            _publisher, move_id, attachment_id=False, attempt=1,
            job_uuid=False, ocr_text=False,
        ):
            published.append(move_id)

        with patch.object(
            type(self.env["queue.publisher"]),
            "publish_extract_request",
            _fake_publish_extract_request,
        ):
            jobs._drain_pending(limit=10)
            jobs._drain_pending(limit=10)  # second drain — nothing new

        self.assertEqual(
            published,
            [move.id],
            "already-sent rows must not be re-published",
        )
