"""Idempotency ledger for queue-applied results.

v0.9 — the uniqueness guard proving a redelivered job never creates a second
draft ``account.move``.

``account.move`` results arrive over AMQP with at-least-once delivery: a
crash between "worker published extract.done" and "Odoo consumer committed
the apply" redelivers the message. The consumer must therefore apply each
``job_uuid`` exactly once. The ledger does that with the database itself:

    ``invoice.agent.applied.job`` (job_uuid UNIQUE)

Before applying a result, the consumer runs ``INSERT ... ON CONFLICT DO
NOTHING`` for the ``job_uuid``. If the insert reports zero rows created, the
job was already applied — the redelivered message is a no-op. If one row was
created (or the job is new), the apply proceeds. Row creation and the apply
commit in the same transaction, so a crash mid-apply leaves no ledger row
and the next redelivery retries safely.

This mirrors the classic transactional-outbox pattern (ADR-004) on the
consumer side: the dedupe decision is atomic with the work it guards.
"""

from odoo import fields, models


class InvoiceAgentAppliedJob(models.Model):
    _name = "invoice.agent.applied.job"
    _description = "Idempotency ledger: job_uuid values already applied"
    _rec_name = "job_uuid"

    job_uuid = fields.Char(
        string="Job UUID",
        required=True,
        index=True,
        copy=False,
        help="UUID of an extract.done result that was already applied. "
        "UNIQUE — a redelivered message for the same uuid is a no-op.",
    )
    move_id = fields.Many2one(
        comodel_name="account.move",
        string="Invoice",
        ondelete="set null",
        index=True,
        help="The account.move this ledger row applied the result to.",
    )
    applied_at = fields.Datetime(
        string="Applied At",
        default=fields.Datetime.now,
        readonly=True,
        help="When the result was applied (first delivery only).",
    )

    _sql_constraints = [
        (
            "job_uuid_unique",
            "UNIQUE(job_uuid)",
            "A job result may only be applied once per job_uuid.",
        ),
    ]
