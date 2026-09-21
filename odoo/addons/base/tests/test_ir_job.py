import time
from datetime import timedelta
from unittest.mock import patch

import psycopg.errors

import odoo
from odoo import api, fields
from odoo.exceptions import (
    RetryableJobError,
    TerminalJobError,
    UserError,
    ValidationError,
)
from odoo.libs import backoff
from odoo.modules.registry import Registry
from odoo.service import get_job_real_time_budget
from odoo.tests import common
from odoo.tests.common import BaseCase, TransactionCase
from odoo.tools import SQL, mute_logger

from odoo.addons.base.models import ir_job
from odoo.addons.base.models.ir_cron import IrCron
from odoo.addons.base.models.ir_job import IrJob


@api.job(channel="root", priority=7, max_retries=2)
def _ir_job_test_append(self, suffix="!"):
    for record in self:
        record.name += suffix


@api.job
def _ir_job_test_boom(self, retryable=False, seconds=None):
    if retryable:
        raise RetryableJobError("try me later", seconds=seconds)
    raise ValueError("boom")


@api.job(max_defers=3)
def _ir_job_test_poll(self, ready=False, seconds=60):
    for record in self:
        record.name += "."
    if not ready:
        self.env["ir.job"]._defer(seconds, reason="not ready yet")


@api.job(idle_timeout=900)
def _ir_job_test_idle(self):
    self.env.cr.execute("SHOW idle_in_transaction_session_timeout")
    for record in self:
        record.name = f"idle {self.env.cr.fetchone()[0]}"


def _isolate_queue(env):
    env.cr.execute(
        "UPDATE ir_job SET state = 'cancelled'"
        " WHERE state IN ('wait_deps', 'scheduled', 'pending', 'started')"
    )
    env.cr.execute("DELETE FROM ir_job_channel")


class TestIrJob(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner_cls = type(cls.env["res.partner"])
        for func in (
            _ir_job_test_append,
            _ir_job_test_boom,
            _ir_job_test_poll,
            _ir_job_test_idle,
        ):
            setattr(cls.partner_cls, func.__name__, func)
            cls.addClassCleanup(delattr, cls.partner_cls, func.__name__)
        cls.partner = cls.env["res.partner"].create({"name": "job target"})
        _isolate_queue(cls.env)

    def _claim(self):
        return IrJob._claim_next(self.env.cr, "test:0")

    def test_delayed_enqueues_pending_job(self):
        job = self.partner.delayed()._ir_job_test_append("?")
        self.assertEqual(job.state, "pending")
        self.assertEqual(job.model_name, "res.partner")
        self.assertEqual(job.method_name, "_ir_job_test_append")
        self.assertEqual(job.record_ids, self.partner.ids)
        self.assertEqual(job.args, ["?"])
        self.assertEqual(job.kwargs, {})
        self.assertEqual(job.channel, "root")
        self.assertEqual(job.priority, 7)
        self.assertEqual(job.max_retries, 2)
        self.assertEqual(job.user_id.id, self.env.uid)
        self.assertTrue(job.uuid)
        self.assertFalse(job.eta)

    def test_delayed_overrides_decorator_defaults(self):
        job = self.partner.delayed(
            priority=1, channel="heavy", max_retries=9, eta=3600
        )._ir_job_test_append()
        self.assertEqual(job.priority, 1)
        self.assertEqual(job.channel, "heavy")
        self.assertEqual(job.max_retries, 9)
        self.assertTrue(job.eta > fields.Datetime.now() + timedelta(minutes=55))

    def test_delayed_rejects_undecorated_method(self):
        with self.assertRaises(UserError):
            self.partner.delayed().write({"name": "nope"})

    def test_delayed_rejects_unserializable_args(self):
        with self.assertRaises(UserError):
            self.partner.delayed()._ir_job_test_append(object())

    def test_context_is_allowlisted(self):
        records = self.partner.with_context(lang="en_US", secret="s3cr3t")
        job = records.delayed()._ir_job_test_append()
        self.assertEqual(job.context.get("lang"), "en_US")
        self.assertNotIn("secret", job.context)

    def test_identity_key_dedup(self):
        first = self.partner.delayed(identity_key="once")._ir_job_test_append()
        twin = self.partner.delayed(identity_key="once")._ir_job_test_append()
        self.assertEqual(first.id, twin.id)
        first.sudo().write({"state": "done"})
        first.env.flush_all()
        third = self.partner.delayed(identity_key="once")._ir_job_test_append()
        self.assertNotEqual(first.id, third.id)

    def test_claim_respects_priority_and_eta(self):
        low = self.partner.delayed(priority=20)._ir_job_test_append()
        high = self.partner.delayed(priority=1)._ir_job_test_append()
        future = self.partner.delayed(priority=0, eta=3600)._ir_job_test_append()

        claimed = self._claim()
        self.assertEqual(claimed["id"], high.id)
        high.invalidate_recordset()
        self.assertEqual(high.state, "started")
        self.assertEqual(high.worker_ident, "test:0")

        claimed = self._claim()
        self.assertEqual(claimed["id"], low.id, "priority order, not capacity order")

        self.assertIsNone(self._claim())
        self.assertEqual(
            future.state, "scheduled", "a job waiting on its clock is not claimable"
        )

    def test_delayed_work_is_kept_out_of_the_claim_index(self):
        later = self.partner.delayed(eta=3600)._ir_job_test_append()
        soon = self.partner.delayed()._ir_job_test_append()
        self.assertEqual(later.state, "scheduled")
        self.assertEqual(soon.state, "pending")

        self.env.cr.execute(
            "SELECT count(*) FROM ir_job WHERE state = 'pending'"
            " AND eta IS NOT NULL AND eta > (now() AT TIME ZONE 'UTC')"
        )
        self.assertEqual(
            self.env.cr.fetchone()[0], 0, "no delayed row may sit in the claim index"
        )

        claimed = self._claim()
        self.assertEqual(claimed["id"], soon.id)

    def test_promotion_moves_a_job_over_when_its_clock_runs_out(self):
        job = self.partner.delayed(eta=3600)._ir_job_test_append()
        self.assertEqual(IrJob._promote_due_jobs(self.env.cr), 0, "not due yet")

        self.env.cr.execute(
            "UPDATE ir_job SET eta = (now() AT TIME ZONE 'UTC') - interval '1 second'"
            " WHERE id = %s",
            (job.id,),
        )
        self.assertEqual(IrJob._promote_due_jobs(self.env.cr), 1)
        job.invalidate_recordset()
        self.assertEqual(job.state, "pending")
        self.assertEqual(self._claim()["id"], job.id)

    def test_a_scheduled_job_can_be_cancelled_and_run_manually(self):
        job = self.partner.delayed(eta=3600)._ir_job_test_append(" now")
        job.action_run_now()
        self.assertEqual(job.state, "done")

        other = self.partner.delayed(eta=3600)._ir_job_test_append()
        other.action_cancel()
        self.assertEqual(other.state, "cancelled")

    def test_scheduled_job_still_holds_its_identity_key(self):
        first = self.partner.delayed(
            eta=3600, identity_key="nightly"
        )._ir_job_test_append()
        self.assertEqual(first.state, "scheduled")
        twin = self.partner.delayed(identity_key="nightly")._ir_job_test_append()
        self.assertEqual(first.id, twin.id)

    def test_claim_respects_channel_capacity(self):
        for _ in range(3):
            self.partner.delayed(channel="bulk")._ir_job_test_append()

        self.env["ir.job.channel"].create({"name": "bulk", "capacity": 2})
        self.env.flush_all()
        self.assertIsNotNone(self._claim())
        self.assertIsNotNone(self._claim(), "up to the declared capacity")
        self.assertIsNone(self._claim(), "and no further")

    def test_an_undeclared_channel_is_not_capped_at_one(self):
        for _ in range(4):
            self.partner.delayed(channel="uncapped")._ir_job_test_append()
        self.env.flush_all()

        claimed = [self._claim() for _ in range(4)]
        self.assertTrue(
            all(claimed),
            "a channel with no ir.job.channel record is bounded by the worker "
            "fleet, not silently serialised to one job at a time",
        )
        self.assertIsNone(self._claim())

    def test_claim_orders_across_every_runnable_channel(self):
        wanted = []
        for index, channel in enumerate(("alpha", "beta", "gamma", "delta")):
            self.partner.delayed(channel=channel, priority=90 - index)
            wanted.append(
                (
                    90 - index,
                    self.partner.delayed(channel=channel, priority=90 - index)
                    ._ir_job_test_append()
                    .id,
                )
            )
        self.env.flush_all()

        claimed = []
        while job := self._claim():
            claimed.append(job["id"])
            self.env.cr.execute(
                "UPDATE ir_job SET state = 'done' WHERE id = %s", (job["id"],)
            )

        self.assertEqual(
            claimed,
            [job_id for _priority, job_id in sorted(wanted)],
            "priority order is global, not per channel: restricting the claim to "
            "the runnable channels must not cost the ordering, and must not be "
            "paid for with a sort of the whole backlog either",
        )

    def test_runnable_channels_skips_saturated_paused_and_idle_ones(self):
        self.env["ir.job.channel"].create(
            [
                {"name": "full", "capacity": 1},
                {"name": "room", "capacity": 2},
                {"name": "off", "capacity": 9, "active": False},
                {"name": "idle", "capacity": 9},
            ]
        )
        for channel in ("full", "room", "off"):
            self.partner.delayed(channel=channel)._ir_job_test_append()
            self.partner.delayed(channel=channel)._ir_job_test_append()
        self.env.flush_all()
        self.env.cr.execute(
            "UPDATE ir_job SET state = 'started' WHERE channel IN ('full', 'room')"
            " AND id = (SELECT min(id) FROM ir_job b WHERE b.channel = ir_job.channel)"
        )

        self.assertEqual(
            sorted(IrJob._get_runnable_channels(self.env.cr)),
            ["room"],
            "'full' is at capacity, 'off' is paused, 'idle' has no pending work",
        )
        self.assertEqual(
            IrJob._get_runnable_channels(self.env.cr, channels=["off"]),
            [],
            "and the worker's own channel filter still applies",
        )

    def test_run_claimed_executes_and_completes_atomically(self):
        self.partner.delayed()._ir_job_test_append(" ran")
        job = self._claim()
        IrJob._run_claimed(self.env.cr, job)
        self.env.invalidate_all()
        self.assertEqual(self.partner.name, "job target ran")
        record = self.env["ir.job"].browse(job["id"])
        self.assertEqual(record.state, "done")
        self.assertTrue(record.done_at)

    def test_a_job_that_waits_outside_gets_its_own_idle_budget(self):
        self.env.cr.execute("SHOW idle_in_transaction_session_timeout")
        server_default = self.env.cr.fetchone()[0]
        self.partner.delayed()._ir_job_test_idle()
        IrJob._run_claimed(self.env.cr, self._claim())
        self.env.invalidate_all()
        self.assertEqual(self.partner.name, "idle 15min")
        self.assertNotEqual(server_default, "15min")

    def test_an_idle_budget_must_be_positive(self):
        def _job(self):
            return None

        with self.assertRaises(ValueError):
            api.job(idle_timeout=0)(_job)

    def test_run_claimed_refuses_undecorated_method(self):
        self.partner.delayed()._ir_job_test_append()
        job = self._claim()
        job["method_name"] = "write"
        with self.assertRaises(TerminalJobError):
            IrJob._run_claimed(self.env.cr, job)

    def test_run_claimed_refuses_a_vanished_model_terminally(self):
        self.partner.delayed()._ir_job_test_append()
        job = self._claim()
        job["model_name"] = "res.partner.uninstalled"
        with self.assertRaises(TerminalJobError):
            IrJob._run_claimed(self.env.cr, job)

    def test_undispatchable_job_does_not_climb_the_backoff_ladder(self):
        self.partner.delayed(max_retries=5)._ir_job_test_append()
        job = self._claim()
        job["method_name"] = "write"
        with self.assertRaises(TerminalJobError) as caught:
            IrJob._run_claimed(self.env.cr, job)
        IrJob._record_failure(self.env.cr, job, caught.exception)
        record = self.env["ir.job"].browse(job["id"])
        record.invalidate_recordset()
        self.assertEqual(record.state, "failed")
        self.assertEqual(record.retry, 0, "not one retry was spent")

    def test_failure_retries_with_backoff_then_fails(self):
        self.partner.delayed(max_retries=1)._ir_job_test_boom(
            retryable=True, seconds=42
        )
        job = self._claim()
        with self.assertRaises(RetryableJobError):
            IrJob._run_claimed(self.env.cr, job)
        IrJob._record_failure(self.env.cr, job, RetryableJobError("x", seconds=42))

        record = self.env["ir.job"].browse(job["id"])
        self.assertEqual(record.state, "scheduled", "backing off is waiting on a clock")
        self.assertEqual(record.retry, 1)
        self.assertEqual(record.exc_name, "RetryableJobError")
        delta = record.eta - fields.Datetime.now()
        self.assertTrue(timedelta(seconds=37) < delta < timedelta(seconds=47))
        self.assertIsNone(self._claim(), "not claimable while it is backing off")

        self.env.cr.execute("UPDATE ir_job SET eta = NULL WHERE id = %s", (job["id"],))
        self.assertEqual(IrJob._promote_due_jobs(self.env.cr), 1)
        record.invalidate_recordset()
        self.assertEqual(record.state, "pending")
        job = self._claim()
        self.assertEqual(job["id"], record.id)
        IrJob._record_failure(self.env.cr, job, ValueError("boom"))
        record.invalidate_recordset()
        self.assertEqual(record.state, "failed")
        self.assertEqual(record.exc_name, "ValueError")
        self.assertTrue(record.done_at)

    def test_the_retry_ladder_is_the_shared_jittered_backoff(self):
        for retry, expected in enumerate((10, 20, 40, 80, 160)):
            self.assertEqual(
                backoff.get_bound(
                    retry + 1,
                    base=ir_job.RETRY_BACKOFF_BASE_S,
                    cap=ir_job.RETRY_BACKOFF_MAX_S,
                ),
                expected,
            )
        record = self.partner.delayed(max_retries=3)._ir_job_test_boom()
        job = self._claim()
        with patch.object(ir_job.backoff, "get_delay", return_value=42.0) as delay:
            IrJob._record_failure(self.env.cr, job, ValueError("boom"))
        delay.assert_called_once_with(
            1, base=ir_job.RETRY_BACKOFF_BASE_S, cap=ir_job.RETRY_BACKOFF_MAX_S
        )
        record.invalidate_recordset()
        self.assertEqual(record.retry, 1)
        self.assertAlmostEqual(
            (record.eta - self.env.cr.now().replace(tzinfo=None)).total_seconds(),
            42.0,
            delta=2,
            msg="the eta is the jittered delay, so retries of one failure spread out",
        )

    def test_only_a_retryable_error_dictates_its_own_delay(self):
        class SecondsCarrier(ValueError):
            seconds = 0

        self.partner.delayed(max_retries=5)._ir_job_test_boom()
        job = self._claim()
        IrJob._record_failure(self.env.cr, job, SecondsCarrier("boom"))

        record = self.env["ir.job"].browse(job["id"])
        self.assertEqual(
            record.state,
            "scheduled",
            "an unrelated exception that happens to carry a .seconds attribute "
            "does not get to bypass the backoff ladder",
        )
        self.assertGreater(record.eta, self.env.cr.now().replace(tzinfo=None))

    def test_vanished_records_fail_the_job_terminally(self):
        doomed = self.env["res.partner"].create({"name": "doomed"})
        doomed.delayed()._ir_job_test_append()
        self.env.flush_all()
        doomed.unlink()

        job = self._claim()
        with self.assertRaises(TerminalJobError):
            IrJob._run_claimed(self.env.cr, job)

    def test_a_job_that_succeeds_never_pays_for_the_existence_check(self):
        self.partner.delayed()._ir_job_test_append()
        self.env.flush_all()
        job = self._claim()

        with patch.object(type(self.partner), "exists", autospec=True) as exists:
            IrJob._run_claimed(self.env.cr, job)

        exists.assert_not_called()
        self.assertEqual(
            self.env["ir.job"].browse(job["id"]).state,
            "done",
            "the vanished-records check belongs on the failure path: run eagerly "
            "it cost one query per job -- 9.0 statements per job against 8.0 -- "
            "to catch a case almost no job hits",
        )

    def test_requeue_restores_the_deferral_budget(self):
        job = self.partner.delayed()._ir_job_test_poll()
        self.env.flush_all()
        job.sudo().write(
            {
                "state": "failed",
                "retry": 5,
                "defer_count": 3,
                "max_defers": 3,
                "defer_reason": "not ready yet",
            }
        )
        self.env.flush_all()

        job.action_requeue()
        self.assertEqual(job.state, "pending")
        self.assertEqual(job.retry, 0)
        self.assertEqual(
            job.defer_count,
            0,
            "a job that died of deferral exhaustion has to be able to defer "
            "again, or requeueing it just reproduces the same terminal error",
        )
        self.assertFalse(job.defer_reason)

    def test_reaper_requeues_dead_started_jobs(self):
        job = self.partner.delayed()._ir_job_test_append()
        self.env.cr.execute(
            "UPDATE ir_job SET state = 'started',"
            " started_at = (now() AT TIME ZONE 'UTC') - interval '5 minutes'"
            " WHERE id = %s",
            (job.id,),
        )
        IrJob._reap_dead_jobs(self.env.cr)
        job.invalidate_recordset()
        self.assertEqual(job.state, "pending")
        self.assertEqual(job.retry, 1)
        self.assertEqual(job.exc_name, "WorkerDied")

    def test_reaper_spares_recent_and_locked_jobs(self):
        fresh = self.partner.delayed()._ir_job_test_append()
        self.env.cr.execute(
            "UPDATE ir_job SET state = 'started',"
            " started_at = (now() AT TIME ZONE 'UTC') WHERE id = %s",
            (fresh.id,),
        )
        IrJob._reap_dead_jobs(self.env.cr)
        fresh.invalidate_recordset()
        self.assertEqual(fresh.state, "started", "inside the grace period")

    def test_reaper_fails_job_with_exhausted_budget(self):
        job = self.partner.delayed(max_retries=0)._ir_job_test_append()
        self.env.cr.execute(
            "UPDATE ir_job SET state = 'started',"
            " started_at = (now() AT TIME ZONE 'UTC') - interval '5 minutes'"
            " WHERE id = %s",
            (job.id,),
        )
        IrJob._reap_dead_jobs(self.env.cr)
        job.invalidate_recordset()
        self.assertEqual(job.state, "failed")

    def test_chain_releases_on_completion(self):
        j1 = self.partner.delayed()._ir_job_test_append(" a")
        j2 = self.partner.delayed(after=j1)._ir_job_test_append(" b")
        self.assertEqual(j2.state, "wait_deps")
        self.assertEqual(j2.depends_on_ids, j1)
        self.assertEqual(j1.dependent_ids, j2)

        claimed = self._claim()
        self.assertEqual(claimed["id"], j1.id, "wait_deps must not be claimable")
        IrJob._run_claimed(self.env.cr, claimed)
        j2.invalidate_recordset()
        self.assertEqual(j2.state, "pending", "released atomically with j1's done")

        claimed = self._claim()
        self.assertEqual(claimed["id"], j2.id)
        IrJob._run_claimed(self.env.cr, claimed)
        self.env.invalidate_all()
        self.assertEqual(self.partner.name, "job target a b")

    def test_fan_in_waits_for_all_dependencies(self):
        j1 = self.partner.delayed()._ir_job_test_append()
        j2 = self.partner.delayed(channel="other")._ir_job_test_append()
        j3 = self.partner.delayed(after=j1 | j2)._ir_job_test_append()

        IrJob._run_claimed(self.env.cr, self._claim())
        j3.invalidate_recordset()
        self.assertEqual(j3.state, "wait_deps", "one of two dependencies done")
        IrJob._run_claimed(self.env.cr, self._claim())
        j3.invalidate_recordset()
        self.assertEqual(j3.state, "pending", "all dependencies done")

    def test_enqueue_after_done_dependency_is_pending(self):
        j1 = self.partner.delayed()._ir_job_test_append()
        IrJob._run_claimed(self.env.cr, self._claim())
        j2 = self.partner.delayed(after=j1)._ir_job_test_append()
        self.assertEqual(j2.state, "pending")

    def test_enqueue_after_failed_dependency_is_refused(self):
        j1 = self.partner.delayed(max_retries=0)._ir_job_test_boom()
        claimed = self._claim()
        IrJob._record_failure(self.env.cr, claimed, ValueError("boom"))
        with self.assertRaises(UserError):
            self.partner.delayed(after=j1)._ir_job_test_append()

    def test_failure_cascade_cancels_transitive_dependents(self):
        j1 = self.partner.delayed(max_retries=0)._ir_job_test_boom()
        j2 = self.partner.delayed(after=j1)._ir_job_test_append()
        j3 = self.partner.delayed(after=j2)._ir_job_test_append()

        claimed = self._claim()
        IrJob._record_failure(self.env.cr, claimed, ValueError("boom"))
        (j1 + j2 + j3).invalidate_recordset()
        self.assertEqual(j1.state, "failed")
        self.assertEqual(j2.state, "cancelled")
        self.assertEqual(j3.state, "cancelled", "cascade is transitive")
        self.assertEqual(j2.exc_name, "DependencyFailed")

    def test_cancel_cascades_to_waiting_dependents(self):
        j1 = self.partner.delayed()._ir_job_test_append()
        j2 = self.partner.delayed(after=j1)._ir_job_test_append()
        j1.action_cancel()
        j2.invalidate_recordset()
        self.assertEqual(j2.state, "cancelled")

    def test_requeue_recomputes_dependency_state(self):
        j1 = self.partner.delayed()._ir_job_test_append()
        j2 = self.partner.delayed(after=j1)._ir_job_test_append()
        j1.action_cancel()
        j2.invalidate_recordset()
        self.assertEqual(j2.state, "cancelled")
        (j1 + j2).action_requeue()
        self.assertEqual(j1.state, "pending")
        self.assertEqual(j2.state, "wait_deps")

    def test_repair_sweep_resolves_stuck_jobs(self):
        j1 = self.partner.delayed()._ir_job_test_append()
        j2 = self.partner.delayed(after=j1)._ir_job_test_append()
        self.env.cr.execute("UPDATE ir_job SET state = 'done' WHERE id = %s", (j1.id,))
        IrJob._release_ready_dependents(self.env.cr)
        j2.invalidate_recordset()
        self.assertEqual(j2.state, "pending")

        j3 = self.partner.delayed()._ir_job_test_append()
        j4 = self.partner.delayed(after=j3)._ir_job_test_append()
        self.env.cr.execute(
            "UPDATE ir_job SET state = 'failed' WHERE id = %s", (j3.id,)
        )
        IrJob._release_ready_dependents(self.env.cr)
        j4.invalidate_recordset()
        self.assertEqual(j4.state, "cancelled")

    def test_requeue_and_cancel_actions(self):
        job = self.partner.delayed()._ir_job_test_append()
        job.action_cancel()
        self.assertEqual(job.state, "cancelled")
        job.action_requeue()
        self.assertEqual(job.state, "pending")
        self.assertEqual(job.retry, 0)
        with self.assertRaises(UserError):
            job.action_requeue()

    def test_run_now_executes_pending_job(self):
        job = self.partner.delayed(eta=3600)._ir_job_test_append(" manual")
        job.action_run_now()
        self.assertEqual(job.state, "done")
        self.assertEqual(job.worker_ident, f"manual:{self.env.uid}")
        self.env.invalidate_all()
        self.assertEqual(self.partner.name, "job target manual")
        with self.assertRaises(UserError):
            job.action_run_now()

    def test_run_now_propagates_business_exception(self):
        job = self.partner.delayed()._ir_job_test_boom()
        with self.assertRaises(ValueError):
            job.action_run_now()

    def test_notify_failed_hook_fires_on_permanent_failure(self):
        job = self.partner.delayed(max_retries=0)._ir_job_test_boom()
        claimed = self._claim()
        exc = ValueError("boom")
        with patch.object(IrJob, "_notify_failed") as hook:
            IrJob._record_failure(self.env.cr, claimed, exc)
        hook.assert_called_once()
        job.invalidate_recordset()
        self.assertEqual(job.state, "failed")

    def test_success_clears_the_previous_failure_trace(self):
        job = self.partner.delayed(max_retries=3)._ir_job_test_boom()
        claimed = self._claim()
        IrJob._record_failure(self.env.cr, claimed, ValueError("boom"))
        job.invalidate_recordset()
        self.assertEqual(job.exc_name, "ValueError")

        self.env.cr.execute("UPDATE ir_job SET eta = NULL WHERE id = %s", (job.id,))
        IrJob._promote_due_jobs(self.env.cr)
        claimed = self._claim()
        claimed["method_name"] = "_ir_job_test_append"
        IrJob._run_claimed(self.env.cr, claimed)
        job.invalidate_recordset()
        self.assertEqual(job.state, "done")
        self.assertFalse(job.exc_name)
        self.assertFalse(job.exc_message)
        self.assertFalse(job.exc_info)
        self.assertEqual(job.retry, 1, "the retry count still records the failure")

    def test_requeue_clears_the_previous_run_traces(self):
        job = self.partner.delayed(max_retries=0)._ir_job_test_boom()
        claimed = self._claim()
        IrJob._record_failure(self.env.cr, claimed, ValueError("boom"))
        job.invalidate_recordset()
        self.assertEqual(job.state, "failed")
        self.assertTrue(job.worker_ident)

        job.action_requeue()
        job.invalidate_recordset()
        self.assertEqual(job.state, "pending")
        self.assertFalse(job.exc_name)
        self.assertFalse(job.exc_info)
        self.assertFalse(job.worker_ident, "names a worker that is not running it")
        self.assertFalse(job.started_at, "reads as liveness to the reaper")

    def test_archived_scheduling_user_is_refused(self):
        user = self.env["res.users"].create(
            {
                "name": "queued then archived",
                "login": "job_archived_user",
                "group_ids": [(6, 0, [self.env.ref("base.group_user").id])],
            }
        )
        self.partner.with_user(user).delayed()._ir_job_test_append()
        user.active = False
        self.env.flush_all()

        claimed = self._claim()
        with self.assertRaisesRegex(TerminalJobError, "archived"):
            IrJob._run_claimed(self.env.cr, claimed)

    def _multi_company_user(self, companies, allowed):
        user = self.env["res.users"].create(
            {
                "name": "multi company",
                "login": "job_multi_company_user",
                "company_id": companies[0].id,
                "company_ids": [(6, 0, companies.ids)],
                "group_ids": [
                    (
                        6,
                        0,
                        [
                            self.env.ref("base.group_user").id,
                            self.env.ref("base.group_partner_manager").id,
                        ],
                    )
                ],
            }
        )
        scoped = self.partner.with_user(user).with_context(
            allowed_company_ids=allowed.ids
        )
        scoped.delayed()._ir_job_test_append()
        self.env.flush_all()
        return user

    def test_revoked_company_is_dropped_from_the_replayed_scope(self):
        kept = self.env["res.company"].create({"name": "kept"})
        revoked = self.env["res.company"].create({"name": "revoked"})
        user = self._multi_company_user(kept + revoked, kept + revoked)
        user.write({"company_ids": [(6, 0, kept.ids)]})
        self.env.flush_all()

        claimed = self._claim()
        with self.assertLogs("odoo.addons.base.models.ir_job", "WARNING") as logs:
            IrJob._run_claimed(self.env.cr, claimed)
        self.assertIn("company scope", logs.output[0])
        record = self.env["ir.job"].browse(claimed["id"])
        record.invalidate_recordset()
        self.assertEqual(record.state, "done", "it ran, in the scope still allowed")

    def test_narrowing_moves_env_company_when_the_first_one_is_revoked(self):
        revoked = self.env["res.company"].create({"name": "revoked head"})
        kept = self.env["res.company"].create({"name": "surviving"})
        user = self._multi_company_user(revoked + kept, revoked + kept)
        user.write({"company_ids": [(6, 0, kept.ids)], "company_id": kept.id})
        self.env.flush_all()

        claimed = self._claim()
        env = odoo.api.Environment(
            self.env.cr, claimed["user_id"], dict(claimed["context"])
        )
        with self.assertLogs("odoo.addons.base.models.ir_job", "WARNING"):
            narrowed = IrJob._narrow_company_scope(env, claimed)
        self.assertEqual(narrowed.companies.ids, [kept.id])
        self.assertEqual(narrowed.company, kept)

    def test_a_superuser_scope_is_never_narrowed(self):
        gone = self.env["res.company"].create({"name": "not the superuser's"})
        job = {
            "id": 0,
            "context": {"allowed_company_ids": [gone.id]},
        }
        env = odoo.api.Environment(
            self.env.cr, odoo.api.SUPERUSER_ID, dict(job["context"])
        )
        self.assertIs(IrJob._narrow_company_scope(env, job), env)
        self.assertEqual(env.companies.ids, [gone.id])

    def test_a_still_valid_company_scope_is_replayed_untouched(self):
        kept = self.env["res.company"].create({"name": "kept a"})
        other = self.env["res.company"].create({"name": "kept b"})
        self._multi_company_user(kept + other, kept + other)
        claimed = self._claim()
        env = odoo.api.Environment(
            self.env.cr, claimed["user_id"], dict(claimed["context"])
        )
        narrowed = IrJob._narrow_company_scope(env, claimed)
        self.assertIs(narrowed, env)
        self.assertEqual(narrowed.companies.ids, [kept.id, other.id])

    def test_permanent_condition_does_not_climb_the_backoff_ladder(self):
        job = self.partner.delayed(max_retries=5)._ir_job_test_append()
        claimed = self._claim()
        IrJob._record_failure(
            self.env.cr, claimed, TerminalJobError("archived, and staying so")
        )
        job.invalidate_recordset()
        self.assertEqual(job.state, "failed")
        self.assertEqual(job.retry, 0, "the budget was never spent one rung at a time")
        self.assertFalse(job.eta, "no rescheduling for a condition that cannot change")

    def test_job_marker_survives_an_override_that_does_not_redecorate(self):

        class Declaring:
            @api.job(channel="heavy", max_retries=3)
            def _sync(self):
                pass

        class Extending(Declaring):
            def _sync(self):
                return super()._sync()

        self.assertIsNone(
            getattr(Extending._sync, "_job_config", None),
            "the override itself carries no marker — that is the whole trap",
        )
        self.assertEqual(
            ir_job._get_job_config(Extending, "_sync"),
            {
                "channel": "heavy",
                "priority": 10,
                "max_retries": 3,
                "max_defers": 100,
            },
            "the declaration is still reachable along the MRO",
        )

    def test_job_marker_is_still_required_somewhere_in_the_chain(self):
        self.assertIsNone(
            ir_job._get_job_config(self.partner_cls, "_compute_display_name")
        )
        with self.assertRaises(UserError):
            self.partner.delayed()._compute_display_name()

    def test_display_name(self):
        job = self.partner.delayed()._ir_job_test_append()
        self.assertEqual(
            job.display_name, f"res.partner._ir_job_test_append (#{job.id})"
        )

    def test_gc_prunes_finished_jobs_by_retention(self):
        done_old = self.partner.delayed()._ir_job_test_append()
        failed_recent = self.partner.delayed()._ir_job_test_append()
        pending = self.partner.delayed()._ir_job_test_append()
        self.env.cr.execute(
            "UPDATE ir_job SET state = 'done',"
            " done_at = (now() AT TIME ZONE 'UTC') - interval '8 days'"
            " WHERE id = %s",
            (done_old.id,),
        )
        self.env.cr.execute(
            "UPDATE ir_job SET state = 'failed',"
            " done_at = (now() AT TIME ZONE 'UTC') - interval '8 days'"
            " WHERE id = %s",
            (failed_recent.id,),
        )
        self.env.invalidate_all()
        removed, more = self.env["ir.job"]._gc_jobs()
        self.assertEqual(removed, 1)
        self.assertFalse(more)
        self.assertFalse(done_old.exists(), "past done retention → pruned")
        self.assertTrue(failed_recent.exists(), "failed keeps the longer window")
        self.assertTrue(pending.exists())

    def test_job_decorator_requires_private_method(self):
        with self.assertRaises(TypeError):

            @api.job
            def public_method(self):
                pass

    def test_bulk_enqueue_queues_a_single_worker_wakeup(self):
        before = len(self.env.cr.postcommit)
        for index in range(20):
            self.partner.delayed()._ir_job_test_append(str(index))
        self.assertEqual(len(self.env.cr.postcommit) - before, 1)

    def test_retryable_error_with_an_explicit_zero_delay_retries_at_once(self):
        self.partner.delayed()._ir_job_test_boom()
        job = self._claim()
        IrJob._record_failure(self.env.cr, job, RetryableJobError("go", seconds=0))
        record = self.env["ir.job"].browse(job["id"])
        self.assertEqual(record.state, "pending")
        self.assertLess(record.eta - fields.Datetime.now(), timedelta(seconds=5))

    def test_a_deferred_job_goes_back_on_the_clock(self):
        self.partner.delayed()._ir_job_test_poll(seconds=90)
        job = self._claim()
        IrJob._run_claimed(self.env.cr, job)
        self.env.invalidate_all()
        record = self.env["ir.job"].browse(job["id"])
        self.assertEqual(record.state, "scheduled")
        self.assertEqual(record.defer_count, 1)
        self.assertEqual(record.defer_reason, "not ready yet")
        self.assertGreater(record.eta - fields.Datetime.now(), timedelta(seconds=60))

    def test_a_deferral_keeps_what_the_job_already_did(self):
        before = self.partner.name
        self.partner.delayed()._ir_job_test_poll()
        job = self._claim()
        IrJob._run_claimed(self.env.cr, job)
        self.assertEqual(self.partner.name, before + ".")

    def test_a_deferral_is_not_a_retry(self):
        self.partner.delayed()._ir_job_test_poll()
        job = self._claim()
        IrJob._run_claimed(self.env.cr, job)
        self.env.invalidate_all()
        record = self.env["ir.job"].browse(job["id"])
        self.assertEqual(record.retry, 0, "a deferral must not spend a retry")
        self.assertFalse(record.exc_name, "nothing went wrong")
        self.assertFalse(record.exc_info)

    def test_a_deferred_job_keeps_its_identity_key(self):
        first = self.partner.delayed(identity_key="poll-1")._ir_job_test_poll()
        job = self._claim()
        IrJob._run_claimed(self.env.cr, job)
        again = self.partner.delayed(identity_key="poll-1")._ir_job_test_poll()
        self.assertEqual(again, first)

    def test_a_deferred_job_runs_again_and_can_finish(self):
        self.partner.delayed()._ir_job_test_poll(seconds=0)
        job = self._claim()
        IrJob._run_claimed(self.env.cr, job)
        self.env.invalidate_all()
        self.assertEqual(self.env["ir.job"].browse(job["id"]).state, "pending")
        job = self._claim()
        job["kwargs"] = {"ready": True}
        IrJob._run_claimed(self.env.cr, job)
        self.env.invalidate_all()
        record = self.env["ir.job"].browse(job["id"])
        self.assertEqual(record.state, "done")
        self.assertEqual(record.defer_count, 1)

    def test_a_job_that_never_finishes_deferring_fails(self):
        self.partner.delayed()._ir_job_test_poll(seconds=0)
        for expected in (1, 2, 3):
            job = self._claim()
            IrJob._run_claimed(self.env.cr, job)
            self.env.invalidate_all()
            self.assertEqual(self.env["ir.job"].browse(job["id"]).defer_count, expected)
        job = self._claim()
        with self.assertRaises(TerminalJobError):
            IrJob._run_claimed(self.env.cr, job)

    def test_defer_outside_a_job_is_a_programming_error(self):
        with self.assertRaises(UserError):
            self.env["ir.job"]._defer(60)

    def test_a_deferral_does_not_release_dependents(self):
        first = self.partner.delayed()._ir_job_test_poll()
        second = self.partner.delayed(after=first)._ir_job_test_append()
        self.assertEqual(second.state, "wait_deps")
        job = self._claim()
        IrJob._run_claimed(self.env.cr, job)
        self.env.invalidate_all()
        self.assertEqual(second.state, "wait_deps")

    def test_failure_records_the_traceback_of_the_exception(self):
        self.partner.delayed()._ir_job_test_boom()
        job = self._claim()
        try:
            raise ValueError("boom")
        except ValueError as exc:
            caught = exc
        IrJob._record_failure(self.env.cr, job, caught)
        record = self.env["ir.job"].browse(job["id"])
        self.assertIn("ValueError: boom", record.exc_info)
        self.assertIn("test_failure_records_the_traceback", record.exc_info)

    def test_archived_channel_is_paused_not_reset_to_capacity_one(self):
        self.partner.delayed(channel="paused")._ir_job_test_append()
        channel = self.env["ir.job.channel"].create(
            {"name": "paused", "capacity": 4, "active": False}
        )
        self.env.flush_all()
        self.assertIsNone(self._claim())

        channel.active = True
        self.env.flush_all()
        self.assertIsNotNone(self._claim())

    def test_channel_counts_running_and_pending_jobs(self):
        channel = self.env["ir.job.channel"].create({"name": "counted", "capacity": 5})
        self.partner.delayed(channel="counted")._ir_job_test_append()
        self.partner.delayed(channel="counted")._ir_job_test_append()
        self.env.flush_all()
        self.assertEqual((channel.running_count, channel.pending_count), (0, 2))

        self._claim()
        channel.invalidate_recordset()
        self.assertEqual((channel.running_count, channel.pending_count), (1, 1))

    def test_identity_dedup_warns_when_it_drops_the_dependencies(self):
        first = self.partner.delayed(identity_key="chained")._ir_job_test_append()
        blocker = self.partner.delayed()._ir_job_test_append()
        with self.assertLogs("odoo.addons.base.models.ir_job", "WARNING") as logs:
            twin = self.partner.delayed(
                identity_key="chained", after=blocker
            )._ir_job_test_append()
        self.assertEqual(twin, first)
        self.assertFalse(twin.depends_on_ids)
        self.assertIn("deduplicated on identity key", logs.output[0])

    def test_enqueue_after_a_vanished_dependency_is_pending(self):
        gone = self.partner.delayed()._ir_job_test_append()
        gone_id = gone.id
        self.env.cr.execute("DELETE FROM ir_job WHERE id = %s", (gone_id,))
        gone.invalidate_recordset()
        job = self.partner.delayed(after=self.env["ir.job"].browse(gone_id))
        job = job._ir_job_test_append()
        self.assertEqual(job.state, "pending")
        self.assertFalse(job.depends_on_ids)

    def test_enqueue_stamps_the_database_clock(self):
        job = self.partner.delayed(eta=600)._ir_job_test_append()
        self.assertEqual(job.state, "scheduled")
        self.assertEqual(job.create_date, self.env.cr.now().replace(microsecond=0))
        self.env.cr.execute(
            "SELECT %s - (clock_timestamp() AT TIME ZONE 'UTC') FROM ir_job"
            " WHERE id = %s",
            (job.eta, job.id),
        )
        ahead = self.env.cr.fetchone()[0]
        self.assertTrue(
            timedelta(seconds=595) < ahead <= timedelta(seconds=600),
            f"eta should be ~600s of real time away, is {ahead}",
        )

    def test_relative_eta_is_not_eaten_by_an_aged_transaction(self):
        stale = self.env.cr.now() - timedelta(minutes=5)
        self.patch(self.env.cr, "now", lambda: stale)
        job = self.partner.delayed(eta=30)._ir_job_test_append()
        self.assertEqual(job.state, "scheduled")
        self.env.cr.execute(
            "SELECT eta > (clock_timestamp() AT TIME ZONE 'UTC')"
            " FROM ir_job WHERE id = %s",
            (job.id,),
        )
        self.assertTrue(self.env.cr.fetchone()[0], "the 30s delay survived")

    def test_enqueue_state_survives_an_app_clock_running_ahead(self):
        skewed = fields.Datetime.now() + timedelta(hours=1)
        with patch.object(fields.Datetime, "now", staticmethod(lambda: skewed)):
            job = self.partner.delayed(eta=30)._ir_job_test_append()
        self.assertEqual(job.state, "scheduled")
        self.assertGreater(job.eta, self.env.cr.now())
        self.assertIsNone(self._claim(), "and it is indeed not claimable")

    def test_postponing_a_pending_job_moves_it_out_of_the_claim_index(self):
        job = self.partner.delayed()._ir_job_test_append()
        self.assertEqual(job.state, "pending")
        job.write({"eta": self.env.cr.now() + timedelta(hours=1)})
        self.env.flush_all()
        self.assertEqual(job.state, "scheduled")
        self.assertIsNone(self._claim())

    def test_bringing_a_scheduled_job_forward_makes_it_claimable_at_once(self):
        job = self.partner.delayed(eta=3600)._ir_job_test_append()
        self.assertEqual(job.state, "scheduled")
        job.write({"eta": False})
        self.env.flush_all()
        self.assertEqual(job.state, "pending")
        self.assertEqual(self._claim()["id"], job.id)

    def test_delayed_is_not_reachable_over_rpc(self):
        from odoo.exceptions import AccessError
        from odoo.service.model import get_public_method

        with self.assertRaises(AccessError):
            get_public_method(self.env["res.partner"], "delayed")

    def test_delayed_proxy_refuses_dunders(self):
        import copy

        proxy = self.partner.delayed()
        for dunder in ("__deepcopy__", "__copy__", "__iter__", "__len__"):
            with self.subTest(dunder=dunder), self.assertRaises(AttributeError):
                getattr(proxy, dunder)
        with self.assertRaises(TypeError):
            iter(proxy)
        copy.deepcopy(proxy)
        self.assertTrue(callable(proxy._ir_job_test_append))

    def test_realignment_handles_a_multi_record_write(self):
        soon = self.partner.delayed()._ir_job_test_append()
        later = self.partner.delayed(eta=3600)._ir_job_test_append()
        both = soon | later
        both.write({"eta": False})
        self.env.flush_all()
        self.assertEqual(set(both.mapped("state")), {"pending"})

        both.write({"eta": self.env.cr.now() + timedelta(hours=1)})
        self.env.flush_all()
        self.assertEqual(set(both.mapped("state")), {"scheduled"})

    def test_an_explicit_state_write_is_left_alone(self):
        job = self.partner.delayed()._ir_job_test_append()
        job.write({"eta": self.env.cr.now() + timedelta(hours=1), "state": "pending"})
        self.assertEqual(job.state, "pending")

    def test_reaper_handles_a_whole_batch_in_a_fixed_number_of_statements(self):
        jobs = [self.partner.delayed()._ir_job_test_append() for _ in range(8)]
        self.env.cr.execute(
            "UPDATE ir_job SET state = 'started', worker_ident = 'dead:1',"
            " started_at = (now() AT TIME ZONE 'UTC') - interval '5 minutes'"
            " WHERE id = ANY(%s)",
            ([job.id for job in jobs],),
        )
        statements = []
        original = type(self.env.cr).execute

        def counting(cr, query, params=None, **kwargs):
            statements.append(query)
            return original(cr, query, params, **kwargs)

        with patch.object(type(self.env.cr), "execute", counting):
            reaped = IrJob._reap_dead_jobs(self.env.cr)
        self.assertEqual(reaped, 8)
        self.assertLessEqual(len(statements), 4, "one probe, two updates, one unlock")
        self.env.invalidate_all()
        self.assertEqual({job.state for job in jobs}, {"pending"})
        self.assertEqual({job.retry for job in jobs}, {1})

    def test_reaper_skips_a_job_whose_worker_is_still_alive(self):
        job = self.partner.delayed()._ir_job_test_append()
        self.env.cr.execute(
            "UPDATE ir_job SET state = 'started', worker_ident = 'alive:1',"
            " started_at = (now() AT TIME ZONE 'UTC') - interval '5 minutes'"
            " WHERE id = %s",
            (job.id,),
        )
        worker = odoo.db.db_connect(self.env.cr.dbname).cursor()
        try:
            worker.execute(
                "SELECT pg_advisory_lock(hashtextextended('ir_job:' || %s::text, 0))",
                (job.id,),
            )
            self.assertEqual(IrJob._reap_dead_jobs(self.env.cr), 0)
        finally:
            worker.execute(
                "SELECT pg_advisory_unlock(hashtextextended('ir_job:' || %s::text, 0))",
                (job.id,),
            )
            worker.close()
        job.invalidate_recordset()
        self.assertEqual(job.state, "started", "a live worker still owns it")

    def test_reaper_takes_exactly_one_lock_per_candidate(self):
        jobs = [self.partner.delayed()._ir_job_test_append() for _ in range(5)]
        self.env.cr.execute(
            "UPDATE ir_job SET state = 'started', worker_ident = 'dead:1',"
            " started_at = (now() AT TIME ZONE 'UTC') - interval '5 minutes'"
            " WHERE id = ANY(%s)",
            ([job.id for job in jobs],),
        )
        before = self._advisory_locks_held()
        self.env.cr.execute(
            SQL(
                """
                WITH candidates AS MATERIALIZED (
                    SELECT id FROM ir_job
                    WHERE state = 'started' AND worker_ident = 'dead:1'
                    ORDER BY started_at LIMIT 5
                )
                SELECT id FROM candidates WHERE pg_try_advisory_lock(%s)
                """,
                ir_job._advisory_key_sql(SQL.identifier("id")),
            )
        )
        locked = [row[0] for row in self.env.cr.fetchall()]
        try:
            self.assertEqual(len(locked), 5)
            self.assertEqual(self._advisory_locks_held() - before, 5, "one each")
        finally:
            self.env.cr.execute(
                SQL(
                    "SELECT pg_advisory_unlock(%s) FROM unnest(%s::bigint[]) AS id",
                    ir_job._advisory_key_sql(SQL.identifier("id")),
                    locked,
                )
            )
        self.assertEqual(self._advisory_locks_held(), before)

    def test_reaper_splits_a_batch_between_requeue_and_failure(self):
        alive = self.partner.delayed(max_retries=5)._ir_job_test_append()
        spent = self.partner.delayed(max_retries=0)._ir_job_test_append()
        self.env.cr.execute(
            "UPDATE ir_job SET state = 'started', worker_ident = 'dead:1',"
            " started_at = (now() AT TIME ZONE 'UTC') - interval '5 minutes'"
            " WHERE id = ANY(%s)",
            ([alive.id, spent.id],),
        )
        self.assertEqual(IrJob._reap_dead_jobs(self.env.cr), 2)
        self.env.invalidate_all()
        self.assertEqual(alive.state, "pending")
        self.assertEqual(spent.state, "failed")
        self.assertEqual(spent.exc_name, "WorkerDied")

    def test_reaper_releases_the_locks_it_took(self):
        job = self.partner.delayed()._ir_job_test_append()
        self.env.cr.execute(
            "UPDATE ir_job SET state = 'started', worker_ident = 'dead:1',"
            " started_at = (now() AT TIME ZONE 'UTC') - interval '5 minutes'"
            " WHERE id = %s",
            (job.id,),
        )
        before = self._advisory_locks_held()
        savepoint = self.env.cr.savepoint(flush=False)
        self.assertEqual(IrJob._reap_dead_jobs(self.env.cr), 1, "a lock was taken")
        self.assertEqual(
            self._advisory_locks_held(),
            before + 1,
            "held for the rest of the sweep's transaction",
        )
        savepoint.rollback()
        self.assertEqual(
            self._advisory_locks_held(),
            before,
            "and given back by the transaction unwinding, with nothing to leak: "
            "the sweep's own explicit unlock is skipped whenever it raises",
        )

    def _advisory_locks_held(self):
        self.env.cr.execute(
            "SELECT count(*) FROM pg_locks"
            " WHERE locktype = 'advisory' AND pid = pg_backend_pid()"
        )
        return self.env.cr.fetchone()[0]

    def test_maintenance_sweep_is_throttled_per_database(self):
        db_name = self.env.cr.dbname
        ir_job._last_maintenance.pop(db_name, None)
        self.addCleanup(ir_job._last_maintenance.pop, db_name, None)
        db_conn = odoo.db.db_connect(db_name)
        with (
            patch.object(IrJob, "_reap_dead_jobs") as reaper,
            patch.object(IrJob, "_release_ready_dependents"),
        ):
            IrJob._run_maintenance(db_conn)
            IrJob._run_maintenance(db_conn)
        reaper.assert_called_once()


class TestIrJobDependencyCycle(TransactionCase):
    def setUp(self):
        super().setUp()
        _isolate_queue(self.env)

    def test_direct_cycle_is_refused(self):
        job_a = self.env["ir.job"].delayed()._job_ping("a")
        job_b = self.env["ir.job"].delayed(after=job_a)._job_ping("b")
        with self.assertRaises(ValidationError):
            job_a.depends_on_ids = job_b

    def test_indirect_cycle_is_refused(self):
        job_a = self.env["ir.job"].delayed()._job_ping("a")
        job_b = self.env["ir.job"].delayed(after=job_a)._job_ping("b")
        job_c = self.env["ir.job"].delayed(after=job_b)._job_ping("c")
        with self.assertRaises(ValidationError):
            job_a.depends_on_ids = job_c

    def test_cycle_via_the_reverse_side_is_refused(self):
        job_a = self.env["ir.job"].delayed()._job_ping("a")
        job_b = self.env["ir.job"].delayed(after=job_a)._job_ping("b")
        with self.assertRaises(ValidationError):
            job_b.dependent_ids = job_a

    def test_self_dependency_is_refused(self):
        job = self.env["ir.job"].delayed()._job_ping("solo")
        with self.assertRaises(ValidationError):
            job.depends_on_ids = job

    def test_diamond_dependencies_are_allowed(self):
        root = self.env["ir.job"].delayed()._job_ping("root")
        left = self.env["ir.job"].delayed(after=root)._job_ping("left")
        right = self.env["ir.job"].delayed(after=root)._job_ping("right")
        join = self.env["ir.job"].delayed(after=left | right)._job_ping("join")
        self.env.flush_all()
        self.assertEqual(join.state, "wait_deps")
        self.assertEqual(join.depends_on_ids, left | right)


class TestIrJobClaimSnapshot(BaseCase):
    def setUp(self):
        super().setUp()
        self.registry = Registry(common.get_db_name())
        self.addCleanup(self._clear_jobs)
        self._clear_jobs()
        with self.registry.cursor() as cr:
            env = odoo.api.Environment(cr, common.ADMIN_USER_ID, {})
            env["ir.job.channel"].create({"name": "claimtest", "capacity": 100})
            cr.execute(
                "INSERT INTO ir_job (channel, state, priority, model_name,"
                " method_name, user_id, max_retries, retry, create_uid,"
                " create_date, write_uid, write_date) VALUES"
                " ('claimtest','pending',1,'ir.job','_job_ping',1,5,0,1,now(),1,now()),"
                " ('claimtest','pending',2,'ir.job','_job_ping',1,5,0,1,now(),1,now())"
            )

    def _clear_jobs(self):
        with self.registry.cursor() as cr:
            cr.execute("DELETE FROM ir_job_dependency")
            cr.execute("DELETE FROM ir_job WHERE channel = 'claimtest'")
            cr.execute("DELETE FROM ir_job_channel WHERE name = 'claimtest'")

    @mute_logger("odoo.db.cursor")
    def test_claim_recovers_from_a_stale_snapshot(self):
        with self.registry.cursor() as cr_a, self.registry.cursor() as cr_b:
            cr_b.execute("SELECT count(*) FROM ir_job")

            job_a = IrJob._claim_next(cr_a, "snap:a", channels=["claimtest"])
            cr_a.commit()
            self.assertIsNotNone(job_a)

            job_b = IrJob._claim_next(cr_b, "snap:b", channels=["claimtest"])
            cr_b.commit()
            self.assertIsNotNone(job_b, "the stale-snapshot claimer got nothing")
            self.assertNotEqual(job_b["id"], job_a["id"])

    @mute_logger("odoo.db.cursor")
    def test_a_narrower_claim_does_not_skip_past_a_wider_ones_uncommitted_pick(self):
        with self.registry.cursor() as setup:
            env = odoo.api.Environment(setup, common.ADMIN_USER_ID, {})
            env["ir.job.channel"].create(
                [
                    {"name": "inf1_wide", "capacity": 100},
                    {"name": "inf1_narrow", "capacity": 100},
                ]
            )
            setup.execute(
                "INSERT INTO ir_job (channel, state, priority, model_name,"
                " method_name, user_id, max_retries, retry, create_uid,"
                " create_date, write_uid, write_date) VALUES"
                " ('inf1_wide','pending',1,'ir.job','_job_ping',1,5,0,1,now(),1,now()),"
                " ('inf1_narrow','pending',10,'ir.job','_job_ping',1,5,0,1,now(),1,now())"
            )
            setup.commit()
        self.addCleanup(self._clear_inf1)

        with self.registry.cursor() as cr_wide, self.registry.cursor() as cr_narrow:
            job_wide = IrJob._claim_next(
                cr_wide,
                "inf1:wide",
                channels=["inf1_wide", "inf1_narrow"],
                serialise=False,
            )
            self.assertIsNotNone(job_wide)
            self.assertEqual(job_wide["channel"], "inf1_wide")

            job_narrow = IrJob._claim_next(
                cr_narrow, "inf1:narrow", channels=["inf1_narrow"], serialise=False
            )
            cr_wide.commit()
            cr_narrow.commit()

        self.assertIsNotNone(
            job_narrow,
            "a claim scoped to inf1_narrow must not be skipped past its only "
            "pending job by an unrelated, wider claim still in flight",
        )
        self.assertEqual(job_narrow["channel"], "inf1_narrow")

    def _clear_inf1(self):
        with self.registry.cursor() as cr:
            cr.execute(
                "DELETE FROM ir_job WHERE channel IN ('inf1_wide', 'inf1_narrow')"
            )
            cr.execute(
                "DELETE FROM ir_job_channel WHERE name IN ('inf1_wide', 'inf1_narrow')"
            )
            cr.commit()

    @mute_logger("odoo.db.cursor")
    def test_capacity_holds_when_every_claimer_starts_from_a_stale_snapshot(self):
        with self.registry.cursor() as setup:
            env = odoo.api.Environment(setup, common.ADMIN_USER_ID, {})
            env["ir.job.channel"].create({"name": "capsnap", "capacity": 2})
            for _ in range(6):
                env["ir.job"].delayed(channel="capsnap")._job_ping("x")
            env.flush_all()
            setup.commit()
        self.addCleanup(self._clear_capsnap)

        claimers = [self.registry.cursor() for _ in range(6)]
        try:
            for cr in claimers:
                cr.execute("SELECT count(*) FROM ir_job")
            claimed = []
            for cr in claimers:
                job = IrJob._claim_next(cr, "capsnap:0", channels=["capsnap"])
                cr.commit()
                if job is not None:
                    claimed.append(job["id"])
            self.assertEqual(
                len(claimed),
                2,
                "every claimer opened its snapshot before any claim committed, so "
                "each one's capacity count starts stale. The advisory lock does "
                "NOT refresh it -- the snapshot is taken before the lock is "
                "granted. What holds the capacity line is that the claim always "
                "targets the lowest-ordered pending row of the channel, so a "
                "stale claimer collides with the row already taken, gets a "
                "serialization failure, and retries against a fresh snapshot. A "
                "claim that let stale claimers pick different rows would silently "
                "overshoot: measured 9-12 starts against this capacity of 2.",
            )
            self.assertEqual(len(set(claimed)), 2, "and never the same job twice")
        finally:
            for cr in claimers:
                cr.close()

    def _clear_capsnap(self):
        with self.registry.cursor() as cr:
            cr.execute("DELETE FROM ir_job WHERE channel = 'capsnap'")
            cr.execute("DELETE FROM ir_job_channel WHERE name = 'capsnap'")
            cr.commit()

    @mute_logger("odoo.db.cursor")
    def test_a_contended_claim_raises_instead_of_reporting_an_empty_queue(self):
        with self.registry.cursor() as cr:
            real = type(cr).execute

            def always_lose(self, query, *args, **kwargs):
                if "UPDATE ir_job" in str(query):
                    raise psycopg.errors.SerializationFailure("lost again")
                return real(self, query, *args, **kwargs)

            with (
                patch.object(type(cr), "execute", always_lose),
                patch.object(ir_job, "CLAIM_BACKOFF_BASE_S", 0.0001),
                patch.object(ir_job, "CLAIM_BACKOFF_MAX_S", 0.0002),
                self.assertRaises(ir_job.ClaimContended),
            ):
                IrJob._claim_next(cr, "contended:0", channels=["claimtest"])


class TestIrJobMaintenanceSnapshot(BaseCase):
    CHANNEL = "sweeptest"

    def setUp(self):
        super().setUp()
        self.db_name = common.get_db_name()
        self.db_conn = odoo.db.db_connect(self.db_name)
        self.registry = Registry(self.db_name)
        self.addCleanup(self._clear_jobs)
        self._clear_jobs()
        with self.registry.cursor() as cr:
            cr.execute(
                "INSERT INTO ir_job (channel, state, model_name, method_name,"
                " user_id, max_retries, retry, priority, create_uid, create_date,"
                " write_uid, write_date) VALUES"
                " (%s,'done','ir.job','_job_ping',1,5,0,10,1,now(),1,now()),"
                " (%s,'wait_deps','ir.job','_job_ping',1,5,0,10,1,now(),1,now())"
                " RETURNING id",
                (self.CHANNEL, self.CHANNEL),
            )
            self.dependency_id, self.waiter_id = (row[0] for row in cr.fetchall())
            cr.execute(
                "INSERT INTO ir_job_dependency (job_id, depends_on_id) VALUES (%s, %s)",
                (self.waiter_id, self.dependency_id),
            )
            cr.commit()

    def _clear_jobs(self):
        with self.registry.cursor() as cr:
            cr.execute(
                "DELETE FROM ir_job_dependency WHERE job_id IN"
                " (SELECT id FROM ir_job WHERE channel = %s)",
                (self.CHANNEL,),
            )
            cr.execute("DELETE FROM ir_job WHERE channel = %s", (self.CHANNEL,))
            cr.commit()
        ir_job._last_maintenance.pop(self.db_name, None)

    def _promote_the_waiter(self):
        with self.registry.cursor() as other:
            other.execute(
                "UPDATE ir_job SET state = 'pending'"
                " WHERE id = %s AND state = 'wait_deps'",
                (self.waiter_id,),
            )
            other.commit()

    def _state(self, job_id):
        with self.registry.cursor() as cr:
            cr.execute("SELECT state FROM ir_job WHERE id = %s", (job_id,))
            return cr.fetchone()[0]

    def test_pass_survives_a_lost_maintenance_race(self):
        with self.registry.cursor() as cr:
            cr.execute(
                "INSERT INTO ir_job (channel, state, model_name, method_name,"
                " user_id, max_retries, retry, priority, create_uid, create_date,"
                " write_uid, write_date) VALUES"
                " (%s,'pending','ir.job','_job_ping',1,5,0,10,1,now(),1,now())"
                " RETURNING id",
                (self.CHANNEL,),
            )
            runnable_id = cr.fetchone()[0]
            cr.commit()

        real_check_version = IrCron._check_version

        def check_version_then_race(pre_cr):
            real_check_version(pre_cr)
            self._promote_the_waiter()

        with (
            patch.object(
                IrCron, "_check_version", staticmethod(check_version_then_race)
            ),
            patch.object(
                IrCron, "_is_any_module_changing", staticmethod(lambda cr: False)
            ),
            patch.object(IrJob, "_notify_workers"),
        ):
            IrJob._process_jobs(self.db_name)

        self.assertEqual(
            self._state(runnable_id),
            "done",
            "the drain was skipped because the maintenance sweep raised",
        )


class TestIrJobEnqueueTarget(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner_cls = type(cls.env["res.partner"])
        setattr(cls.partner_cls, _ir_job_test_append.__name__, _ir_job_test_append)
        cls.addClassCleanup(delattr, cls.partner_cls, _ir_job_test_append.__name__)
        _isolate_queue(cls.env)

    def test_unsaved_records_are_refused(self):
        unsaved = self.env["res.partner"].new({"name": "never saved"})
        self.assertEqual(len(unsaved), 1)
        self.assertEqual(unsaved.ids, [])
        with self.assertRaises(UserError):
            unsaved.delayed()._ir_job_test_append("x")

    def test_saved_records_are_still_accepted(self):
        partner = self.env["res.partner"].create({"name": "saved"})
        job = partner.delayed()._ir_job_test_append("x")
        self.assertEqual(job.record_ids, partner.ids)

    def test_model_level_enqueue_is_still_accepted(self):
        job = self.env["ir.job"].delayed()._job_ping("hi")
        self.assertEqual(job.record_ids, [])


class TestIrJobExecutorLiveness(BaseCase):
    CHANNEL = "livenesstest"

    def setUp(self):
        super().setUp()
        self.registry = Registry(common.get_db_name())
        self.addCleanup(self._clear_jobs)
        self._clear_jobs()

    def _clear_jobs(self):
        with self.registry.cursor() as cr:
            cr.execute("DELETE FROM ir_job WHERE channel = %s", (self.CHANNEL,))

    def _enqueue(self, cr):
        env = odoo.api.Environment(cr, common.ADMIN_USER_ID, {})
        job = env["ir.job"].delayed(channel=self.CHANNEL)._job_ping("manual")
        env.flush_all()
        cr.commit()
        return env["ir.job"].browse(job.id)

    @mute_logger("odoo.addons.base.models.ir_job")
    def test_reaper_spares_a_job_running_manually(self):
        with self.registry.cursor() as cr_run, self.registry.cursor() as cr_reap:
            job = self._enqueue(cr_run)

            def _commit_and_hang(cr, claimed):
                cr.commit()
                with patch.object(ir_job, "DEAD_JOB_GRACE_S", -1):
                    IrJob._reap_dead_jobs(cr_reap)
                cr_reap.commit()

            with patch.object(IrJob, "_run_claimed", staticmethod(_commit_and_hang)):
                job.action_run_now()

            cr_reap.execute("SELECT state FROM ir_job WHERE id = %s", (job.id,))
            self.assertEqual(
                cr_reap.fetchone()[0],
                "started",
                "the reaper requeued a job that was running right then",
            )

    @mute_logger("odoo.addons.base.models.ir_job", "odoo.db.cursor")
    def test_run_now_releases_its_lock_after_an_aborted_transaction(self):
        def _sql_boom(cr, claimed):
            cr.execute("SELECT 1/0")

        with self.registry.cursor() as cr_run, self.registry.cursor() as cr_other:
            job = self._enqueue(cr_run)
            with (
                patch.object(IrJob, "_run_claimed", staticmethod(_sql_boom)),
                self.assertRaises(psycopg.errors.DivisionByZero),
            ):
                job.action_run_now()
            cr_run.rollback()
            cr_run.execute(
                "SELECT count(*) FROM pg_locks"
                " WHERE locktype = 'advisory' AND pid = pg_backend_pid()"
            )
            self.assertEqual(
                cr_run.fetchone()[0],
                0,
                "the liveness lock must be released once the connection is usable",
            )
            other_env = odoo.api.Environment(cr_other, common.ADMIN_USER_ID, {})
            other_job = other_env["ir.job"].browse(job.id)
            self.assertEqual(other_job.state, "pending", "the claim was rolled back")
            with patch.object(IrJob, "_run_claimed", staticmethod(_sql_boom)):
                with self.assertRaises(psycopg.errors.DivisionByZero):
                    other_job.action_run_now()
            cr_other.rollback()

    def test_the_claim_is_committed_before_the_liveness_lock(self):
        with self.registry.cursor() as cr, self.registry.cursor() as observer:
            self._enqueue(cr)
            job = IrJob._claim_next(cr, "order:0")
            cr.commit()
            with ir_job._job_session_lock(cr, job["id"]):
                observer.execute("SELECT state FROM ir_job WHERE id = %s", (job["id"],))
                self.assertEqual(
                    observer.fetchone()[0],
                    "started",
                    "the claim has to be committed before the per-job lock is "
                    "taken: taking the lock first inverts the order against "
                    "action_run_now and PostgreSQL kills the worker for it",
                )
            cr.execute("UPDATE ir_job SET state = 'done' WHERE id = %s", (job["id"],))
            cr.commit()

    @mute_logger("odoo.addons.base.models.ir_job")
    def test_a_manual_run_and_a_worker_claim_do_not_deadlock(self):
        with self.registry.cursor() as cr_worker, self.registry.cursor() as cr_ui:
            job = self._enqueue(cr_worker)
            claimed = IrJob._claim_next(cr_worker, "worker:0")
            cr_worker.commit()

            ui_job = odoo.api.Environment(cr_ui, common.ADMIN_USER_ID, {})[
                "ir.job"
            ].browse(job.id)
            with self.assertRaises(UserError):
                ui_job.action_run_now()

            with ir_job._job_session_lock(cr_worker, claimed["id"]):
                pass
            cr_worker.execute(
                "UPDATE ir_job SET state = 'done' WHERE id = %s", (claimed["id"],)
            )
            cr_worker.commit()

    def test_second_manual_run_is_refused_instead_of_blocking(self):
        with self.registry.cursor() as cr_run, self.registry.cursor() as cr_other:
            job = self._enqueue(cr_run)
            other = odoo.api.Environment(cr_other, common.ADMIN_USER_ID, {})[
                "ir.job"
            ].browse(job.id)

            def _run_concurrently(cr, claimed):
                with self.assertRaises(UserError):
                    other.action_run_now()

            with patch.object(IrJob, "_run_claimed", staticmethod(_run_concurrently)):
                job.action_run_now()


@common.tagged("post_install", "-at_install")
class TestIrJobDrainLoop(BaseCase):
    CHANNEL = "draintest"

    def setUp(self):
        super().setUp()
        self.db_name = common.get_db_name()
        self.registry = Registry(self.db_name)
        self.addCleanup(self._clear_jobs)
        self._clear_jobs()

    def _clear_jobs(self):
        with self.registry.cursor() as cr:
            cr.execute("DELETE FROM ir_job WHERE channel = %s", (self.CHANNEL,))

    def _enqueue(self, count):
        with self.registry.cursor() as cr:
            env = odoo.api.Environment(cr, common.ADMIN_USER_ID, {})
            for index in range(count):
                env["ir.job"].delayed(channel=self.CHANNEL)._job_ping(str(index))
            env.flush_all()
            cr.commit()

    def _states(self):
        with self.registry.cursor() as cr:
            cr.execute(
                "SELECT state, count(*) FROM ir_job WHERE channel = %s GROUP BY state",
                (self.CHANNEL,),
            )
            return dict(cr.fetchall())

    def test_drain_runs_the_queue_and_reports_it_is_empty(self):
        self._enqueue(3)
        with patch.object(ir_job.IrJob, "_notify_workers"):
            deadlined = IrJob._claim_and_run_loop(
                self.db_name, channels=[self.CHANNEL], deadline=time.monotonic() + 60
            )
        self.assertFalse(deadlined)
        self.assertEqual(self._states(), {"done": 3})

    def test_drain_yields_on_its_deadline_and_notifies(self):
        self._enqueue(2)
        with patch.object(ir_job.IrJob, "_notify_workers") as notify:
            deadlined = IrJob._claim_and_run_loop(
                self.db_name, channels=[self.CHANNEL], deadline=time.monotonic() - 1
            )
        self.assertTrue(deadlined)
        notify.assert_called_once_with(self.db_name)
        self.assertEqual(self._states(), {"pending": 2}, "nothing was claimed")

    def test_a_contended_drain_notifies_instead_of_reporting_an_empty_queue(self):
        self._enqueue(2)
        with (
            patch.object(
                ir_job.IrJob,
                "_claim_next",
                staticmethod(
                    lambda *a, **k: (_ for _ in ()).throw(
                        ir_job.ClaimContended("lost every race")
                    )
                ),
            ),
            patch.object(ir_job.IrJob, "_notify_workers") as notify,
            mute_logger("odoo.addons.base.models.ir_job"),
        ):
            deadlined = IrJob._claim_and_run_loop(
                self.db_name, channels=[self.CHANNEL], deadline=time.monotonic() + 60
            )

        self.assertTrue(deadlined, "the pass yielded, it did not drain the queue")
        notify.assert_called_once_with(self.db_name)
        self.assertEqual(
            self._states(),
            {"pending": 2},
            "losing ten claim races in a row is not the same as an empty queue, "
            "and must not put the fleet to sleep on a backlog",
        )

    def test_the_drain_budget_follows_the_job_knob_not_the_cron_one(self):
        budgets = {}
        for real, cron, job, expected in (
            (120, 60, 600, 600),
            (120, 60, -1, 60),
            (120, -1, -1, 120),
            (120, -1, 0, 0),
        ):
            with odoo.tools.config.patch(
                limit_time_real=real,
                limit_time_real_cron=cron,
                limit_time_real_job=job,
            ):
                budgets[(real, cron, job)] = get_job_real_time_budget()
                deadline = IrJob._drain_deadline()
            self.assertEqual(budgets[(real, cron, job)], expected)
            if expected:
                self.assertGreater(
                    deadline,
                    time.monotonic(),
                    "a budget must never yield a deadline in the past",
                )
            else:
                self.assertIsNone(deadline, "0 means no limit")

    def test_an_uncapped_drain_does_not_take_the_serialising_lock(self):
        self._enqueue(2)
        with self.registry.cursor() as cr:
            cr.execute("SELECT count(*) FROM ir_job_channel")
            declared = cr.fetchone()[0]
        self.assertEqual(declared, 0, "no channel declares a capacity here")

        statements = []
        real = odoo.db.cursor.Cursor.execute

        def record(self, query, *args, **kwargs):
            statements.append(str(query))
            return real(self, query, *args, **kwargs)

        with (
            patch.object(odoo.db.cursor.Cursor, "execute", record),
            patch.object(ir_job.IrJob, "_notify_workers"),
        ):
            IrJob._claim_and_run_loop(
                self.db_name, channels=[self.CHANNEL], deadline=time.monotonic() + 60
            )

        self.assertEqual(self._states(), {"done": 2})
        self.assertFalse(
            [q for q in statements if "ir_job_claim" in q],
            "with no capacity declared anywhere there is nothing to ration, and "
            "a fleet-global lock only costs throughput. Four alternating sweeps, "
            "1 -> 12 worker processes: ~1000 -> ~550 claims/s with the lock "
            "always taken, ~1070 -> ~740 with it skipped -- never slower, and "
            "the gap widens with the fleet",
        )

    def test_a_capped_drain_still_takes_the_serialising_lock(self):
        with self.registry.cursor() as cr:
            env = odoo.api.Environment(cr, common.ADMIN_USER_ID, {})
            env["ir.job.channel"].create({"name": self.CHANNEL, "capacity": 4})
            env.flush_all()
            cr.commit()
        self.addCleanup(self._clear_channel)
        self._enqueue(2)

        statements = []
        real = odoo.db.cursor.Cursor.execute

        def record(self, query, *args, **kwargs):
            statements.append(str(query))
            return real(self, query, *args, **kwargs)

        with (
            patch.object(odoo.db.cursor.Cursor, "execute", record),
            patch.object(ir_job.IrJob, "_notify_workers"),
        ):
            IrJob._claim_and_run_loop(
                self.db_name, channels=[self.CHANNEL], deadline=time.monotonic() + 60
            )

        self.assertTrue(
            [q for q in statements if "ir_job_claim" in q],
            "a declared capacity is only enforced because concurrent claimers "
            "are made to collide on one row; see "
            "test_capacity_holds_when_every_claimer_starts_from_a_stale_snapshot",
        )

    def _clear_channel(self):
        with self.registry.cursor() as cr:
            cr.execute("DELETE FROM ir_job_channel WHERE name = %s", (self.CHANNEL,))
            cr.commit()

    def test_drain_publishes_cache_invalidations(self):
        job_model = self.registry["ir.job"]

        @api.job(max_retries=0)
        def _job_test_invalidate(self):
            self.env.registry.clear_cache()

        job_model._job_test_invalidate = _job_test_invalidate
        self.addCleanup(delattr, job_model, "_job_test_invalidate")

        with self.registry.cursor() as cr:
            env = odoo.api.Environment(cr, common.ADMIN_USER_ID, {})
            env["ir.job"].delayed(channel=self.CHANNEL)._job_test_invalidate()
            env.flush_all()
            cr.commit()

        self.registry.cache_invalidated.clear()
        with patch.object(ir_job.IrJob, "_notify_workers"):
            IrJob._claim_and_run_loop(
                self.db_name, channels=[self.CHANNEL], deadline=time.monotonic() + 60
            )
        self.assertEqual(self._states(), {"done": 1})
        self.assertFalse(
            self.registry.cache_invalidated,
            "the invalidation was never published to the other processes",
        )

    def test_a_lost_concurrency_race_is_replayed_not_charged_to_the_job(self):
        job_model = self.registry["ir.job"]
        attempts = []

        @api.job(max_retries=5)
        def _job_test_conflict(self):
            attempts.append(1)
            if len(attempts) < 3:
                raise psycopg.errors.SerializationFailure("lost the race")

        job_model._job_test_conflict = _job_test_conflict
        self.addCleanup(delattr, job_model, "_job_test_conflict")

        with self.registry.cursor() as cr:
            env = odoo.api.Environment(cr, common.ADMIN_USER_ID, {})
            env["ir.job"].delayed(channel=self.CHANNEL)._job_test_conflict()
            env.flush_all()
            cr.commit()

        with (
            patch.object(ir_job.IrJob, "_notify_workers"),
            patch.object(ir_job.time, "sleep"),
        ):
            IrJob._claim_and_run_loop(
                self.db_name, channels=[self.CHANNEL], deadline=time.monotonic() + 60
            )
        self.assertEqual(len(attempts), 3, "replayed until it committed")
        self.assertEqual(self._states(), {"done": 1})
        with self.registry.cursor() as cr:
            cr.execute("SELECT retry FROM ir_job WHERE channel = %s", (self.CHANNEL,))
            self.assertEqual(cr.fetchone()[0], 0, "no budget was spent on it")

    def test_a_real_postgres_serialization_failure_is_replayed(self):
        job_model = self.registry["ir.job"]
        attempts = []
        db_name = self.db_name
        with self.registry.cursor() as cr:
            env = odoo.api.Environment(cr, common.ADMIN_USER_ID, {})
            partner = env["res.partner"].create({"name": "conflict target"})
            partner_id = partner.id
            cr.commit()
        self.addCleanup(self._remove_partner_row, partner_id)
        observed_lock = []
        snapshots = []

        @api.job(max_retries=5)
        def _job_test_real_conflict(self):
            attempts.append(1)
            target = self.env["res.partner"].browse(partner_id)
            snapshots.append(target.comment)
            if len(attempts) == 1:
                with odoo.db.db_connect(db_name).cursor() as other:
                    other.execute(
                        "UPDATE res_partner SET comment = 'outsider' WHERE id = %s",
                        (partner_id,),
                    )
                    other.commit()
            else:
                with odoo.db.db_connect(db_name).cursor() as probe:
                    probe.execute(
                        "SELECT pg_try_advisory_lock("
                        "hashtextextended('ir_job:' || %s::text, 0))",
                        (self.env.context["probe_job_id"],),
                    )
                    observed_lock.append(probe.fetchone()[0])
            target.comment = "the job wrote this"

        job_model._job_test_real_conflict = _job_test_real_conflict
        self.addCleanup(delattr, job_model, "_job_test_real_conflict")

        with self.registry.cursor() as cr:
            env = odoo.api.Environment(cr, common.ADMIN_USER_ID, {})
            enqueued = (
                env["ir.job"].delayed(channel=self.CHANNEL)._job_test_real_conflict()
            )
            cr.execute(
                "UPDATE ir_job SET context = %s WHERE id = %s",
                (f'{{"probe_job_id": {enqueued.id}}}', enqueued.id),
            )
            env.flush_all()
            cr.commit()

        with (
            patch.object(ir_job.IrJob, "_notify_workers"),
            patch.object(ir_job.time, "sleep"),
        ):
            IrJob._claim_and_run_loop(
                self.db_name, channels=[self.CHANNEL], deadline=time.monotonic() + 60
            )

        self.assertEqual(len(attempts), 2, "the first attempt lost a real 40001")
        self.assertEqual(self._states(), {"done": 1})
        with self.registry.cursor() as cr:
            cr.execute("SELECT retry FROM ir_job WHERE channel = %s", (self.CHANNEL,))
            self.assertEqual(cr.fetchone()[0], 0, "no retry budget was spent")
            cr.execute("SELECT comment FROM res_partner WHERE id = %s", (partner_id,))
            self.assertIn("the job wrote this", cr.fetchone()[0])
        self.assertEqual(
            observed_lock,
            [False],
            "the liveness lock was still held across the rollback and replay",
        )
        self.assertEqual(
            snapshots[1],
            "outsider",
            "the replay ran on a fresh snapshot, not the rolled-back one",
        )

    def _remove_partner_row(self, partner_id):
        with self.registry.cursor() as cr:
            cr.execute("DELETE FROM res_partner WHERE id = %s", (partner_id,))
            cr.commit()

    def test_a_race_lost_every_time_still_ends_up_recorded(self):
        job_model = self.registry["ir.job"]
        attempts = []

        @api.job(max_retries=5)
        def _job_test_always_conflict(self):
            attempts.append(1)
            raise psycopg.errors.SerializationFailure("always loses")

        job_model._job_test_always_conflict = _job_test_always_conflict
        self.addCleanup(delattr, job_model, "_job_test_always_conflict")

        with self.registry.cursor() as cr:
            env = odoo.api.Environment(cr, common.ADMIN_USER_ID, {})
            env["ir.job"].delayed(channel=self.CHANNEL)._job_test_always_conflict()
            env.flush_all()
            cr.commit()

        with (
            patch.object(ir_job.IrJob, "_notify_workers"),
            patch.object(ir_job.time, "sleep"),
            mute_logger("odoo.addons.base.models.ir_job"),
        ):
            IrJob._claim_and_run_loop(
                self.db_name, channels=[self.CHANNEL], deadline=time.monotonic() + 60
            )
        self.assertEqual(len(attempts), ir_job.CONCURRENCY_MAX_ATTEMPTS)
        self.assertEqual(self._states(), {"scheduled": 1}, "backing off, as a retry")

    def test_a_signalling_failure_does_not_report_a_finished_job_as_failed(self):
        self._enqueue(1)
        boom = RuntimeError("signalling is down")
        with (
            patch.object(ir_job.IrJob, "_notify_workers"),
            patch.object(type(self.registry), "signal_changes", side_effect=boom),
            self.assertRaises(RuntimeError),
        ):
            IrJob._claim_and_run_loop(
                self.db_name, channels=[self.CHANNEL], deadline=time.monotonic() + 60
            )
        self.assertEqual(
            self._states(), {"done": 1}, "the job committed and stayed committed"
        )


class TestIrJobClaimCapacity(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        _isolate_queue(cls.env)

    def _job(self, channel, state, priority, started=False):
        job = self.env["ir.job"].create(
            {
                "channel": channel,
                "state": state,
                "priority": priority,
                "model_name": "ir.job",
                "method_name": "_job_ping",
                "user_id": self.env.uid,
                "max_retries": 0,
            }
        )
        if started:
            job.started_at = fields.Datetime.now()
        return job

    def test_capacity_is_respected_across_channel_shapes(self):
        self.env["ir.job.channel"].create(
            [
                {"name": "cap2", "capacity": 2},
                {"name": "cap3", "capacity": 3},
                {"name": "off", "capacity": 9, "active": False},
            ]
        )
        for channel, running in (("cap2", 2), ("cap3", 1), ("off", 1)):
            for _ in range(running):
                self._job(channel, "started", 1, started=True)
        wanted = {}
        for priority, channel in enumerate(
            ("cap2", "off", "cap3", "implicit"), start=1
        ):
            wanted[channel] = self._job(channel, "pending", priority).id
        self.env.flush_all()

        claimed = []
        while job := IrJob._claim_next(
            self.env.cr, "cap:0", channels=["cap2", "cap3", "off", "implicit"]
        ):
            claimed.append(job["id"])

        self.assertEqual(
            claimed,
            [wanted["cap3"], wanted["implicit"]],
            "only the channels below capacity are claimable, in priority order",
        )

    def test_backlog_behind_a_saturated_channel_does_not_hide_a_runnable_job(self):
        self.env["ir.job.channel"].create({"name": "full", "capacity": 1})
        self._job("full", "started", 1, started=True)
        for _ in range(50):
            self._job("full", "pending", 1)
        runnable = self._job("free", "pending", 99).id
        self.env.flush_all()

        job = IrJob._claim_next(self.env.cr, "cap:1", channels=["full", "free"])
        self.assertIsNotNone(job)
        self.assertEqual(job["id"], runnable)
