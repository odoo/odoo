import contextlib
import dataclasses
import secrets
import textwrap
import time
from contextlib import closing
from datetime import datetime, timedelta
from unittest.mock import patch

import psycopg
from freezegun import freeze_time

import odoo
from odoo import fields
from odoo.exceptions import AccessError, UserError
from odoo.modules.registry import Registry
from odoo.tests import common
from odoo.tests.common import BaseCase, Like, RecordCapturer, TransactionCase, tagged
from odoo.tools import config, mute_logger
from odoo.tools.constants import CRON_TRIGGER_CHANNEL

from odoo.addons.base.models import ir_cron
from odoo.addons.base.models.ir_cron import (
    CONSECUTIVE_TIMEOUT_FOR_FAILURE,
    MAX_FAIL_TIME,
    MAX_STALLED_ATTEMPTS_PER_RUN,
    MIN_DELTA_BEFORE_DEACTIVATION,
    MIN_FAILURE_COUNT_BEFORE_DEACTIVATION,
    MIN_RUNS_PER_JOB,
    MIN_TIME_PER_JOB,
    PROGRESS_RETENTION_PERIOD,
    RUN_BUDGET_RATIO,
    TRIGGER_RETENTION_PERIOD,
    BadModuleStateError,
    BadVersionError,
    CompletionStatus,
    CronJob,
    IrCron,
    ReadyJob,
)
from odoo.addons.base.tests.common import TransactionCaseWithUserDemo


def make_job(cron, **overrides):
    fields_ = {
        "id": cron.id,
        "cron_name": cron.cron_name,
        "user_id": cron.user_id.id,
        "ir_actions_server_id": cron.ir_actions_server_id.id,
        "active": True,
        "nextcall": cron.nextcall,
        "lastcall": None,
        "repeat_unit": cron.repeat_unit,
        "repeat_interval": cron.repeat_interval,
        "failure_count": 0,
        "first_failure_date": None,
        "progress_id": None,
        "timed_out_counter": 0,
    }
    fields_.update(overrides)
    return CronJob(**fields_)


class CronMixinCase:
    def capture_triggers(self, cron_id=None):
        if isinstance(cron_id, str):
            cron_id = self.env.ref(cron_id).id

        return RecordCapturer(
            model=self.env["ir.cron.trigger"].sudo(),
            domain=[("cron_id", "=", cron_id)] if cron_id else [],
        )

    @classmethod
    def _get_cron_data(cls, env, priority=5):
        unique = secrets.token_urlsafe(8)
        return {
            "name": f"Dummy cron for TestIrCron {unique}",
            "state": "code",
            "code": "",
            "model_id": env.ref("base.model_res_partner").id,
            "model_name": "res.partner",
            "user_id": env.uid,
            "active": True,
            "repeat_interval": 1,
            "repeat_unit": "day",
            "nextcall": fields.Datetime.now() + timedelta(hours=1),
            "lastcall": False,
            "priority": priority,
        }

    @classmethod
    def _get_partner_data(cls, env):
        unique = secrets.token_urlsafe(8)
        return {"name": f"Dummy partner for TestIrCron {unique}"}


class TestIrCron(TransactionCase, CronMixinCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        freezer = freeze_time(cls.cr.now())
        cls.frozen_datetime = freezer.start()
        cls.addClassCleanup(freezer.stop)

        cls.cron = cls.env["ir.cron"].create(cls._get_cron_data(cls.env))
        cls.partner = cls.env["res.partner"].create(cls._get_partner_data(cls.env))

    def setUp(self):
        super().setUp()
        self.partner.write(self._get_partner_data(self.env))
        self.cron.write(self._get_cron_data(self.env))

        domain = [("cron_id", "=", self.cron.id)]
        self.env["ir.cron.trigger"].search(domain).unlink()
        self.env["ir.cron.progress"].search(domain).unlink()

        self.patch(self.env.cr, "now", self.frozen_datetime)

    def _acquire_job(self, cr, cron=None):
        cron = cron if cron is not None else self.cron
        self.env.flush_all()
        job = self.registry["ir.cron"]._acquire_job(cr, cron.id, include_not_ready=True)
        self.assertIsNotNone(job, "the test cron must be acquirable")
        return job

    def test_cron_direct_trigger(self):
        self.cron.code = textwrap.dedent(f"""\
            model.search(
                [("id", "=", {self.partner.id})]
            ).write(
                {{"name": "You have been CRONWNED"}}
            )
        """)

        registry = self.cron.pool
        with (
            self.enter_registry_test_mode(),
            patch.object(
                registry, "cursor", side_effect=registry.cursor, autospec=True
            ) as cursor_method,
        ):
            self.cron.method_direct_trigger()
            self.assertEqual(
                cursor_method.call_count,
                1,
                "Should create a new transaction for direct trigger",
            )

        self.assertEqual(self.cron.lastcall, fields.Datetime.now())
        self.assertEqual(self.partner.name, "You have been CRONWNED")

    def test_a_job_on_a_borrowed_transaction_gives_the_default_env_back(self):
        self.cron.user_id = self.env.ref("base.user_admin")
        self.cron.code = "model.search([], limit=1)"
        caller = self.env(user=self.env.ref("base.user_demo", False) or self.env.user)
        caller.transaction.default_env = caller

        with self.enter_registry_test_mode():
            self.cron.method_direct_trigger()

        self.assertIs(
            caller.transaction.default_env,
            caller,
            "under registry test mode the job shares the caller's transaction; left"
            " as its default environment, every later flush runs as the job's user",
        )

    def test_cron_direct_trigger_exception(self):
        self.cron.code = textwrap.dedent("raise UserError('oops')")
        with (
            self.enter_registry_test_mode(),
            self.assertLogs("odoo.addons.base.models.ir_cron", 40),
            self.registry.cursor() as cron_cr,
        ):
            action = self.cron.with_env(self.env(cr=cron_cr)).method_direct_trigger()

        self.assertNotEqual(action, True)
        action_params = action.pop("params")
        self.assertEqual(
            action, {"type": "ir.actions.client", "tag": "display_exception"}
        )
        self.assertEqual(list(action_params), ["code", "message", "data"])
        self.assertEqual(
            list(action_params["data"]),
            ["name", "message", "arguments", "context", "debug"],
        )

    def test_cron_no_job_ready(self):
        self.cron.nextcall = fields.Datetime.now() + timedelta(days=1)
        self.cron.flush_recordset()

        ready_jobs = self.registry["ir.cron"]._get_jobs_ready(self.cr)
        self.assertNotIn(self.cron.id, [job.id for job in ready_jobs])

    def test_cron_ready_by_nextcall(self):
        self.cron.nextcall = fields.Datetime.now()
        self.cron.flush_recordset()

        ready_jobs = self.registry["ir.cron"]._get_jobs_ready(self.cr)
        self.assertIn(self.cron.id, [job.id for job in ready_jobs])

    def test_cron_ready_by_trigger(self):
        self.cron._trigger()
        self.env["ir.cron.trigger"].flush_model()

        ready_jobs = self.registry["ir.cron"]._get_jobs_ready(self.cr)
        self.assertIn(self.cron.id, [job.id for job in ready_jobs])

    def test_cron_unactive_never_ready(self):
        self.cron.active = False
        self.cron.nextcall = fields.Datetime.now()
        self.env.flush_all()

        ready_jobs = self.registry["ir.cron"]._get_jobs_ready(self.cr)
        self.assertNotIn(self.cron.id, [job.id for job in ready_jobs])

    def test_cron_ready_jobs_order(self):
        cron_avg = self.cron.copy()
        cron_avg.priority = 5

        cron_high = self.cron.copy()
        cron_high.priority = 0

        cron_low = self.cron.copy()
        cron_low.priority = 10

        crons = cron_high | cron_avg | cron_low
        crons.write({"nextcall": fields.Datetime.now()})
        crons.flush_recordset()
        ready_jobs = self.registry["ir.cron"]._get_jobs_ready(self.cr)

        self.assertEqual(
            [job.id for job in ready_jobs if job.id in crons._ids],
            list(crons._ids),
        )

    def test_cron_skip_unactive_triggers(self):
        self.cron.active = False
        self.cron.nextcall = fields.Datetime.now() + timedelta(days=2)
        self.cron.flush_recordset()
        with self.capture_triggers() as capture:
            self.cron._trigger()

        ready_jobs = self.registry["ir.cron"]._get_jobs_ready(self.cr)
        self.assertNotIn(
            self.cron.id,
            [job.id for job in ready_jobs],
            "the cron shouldn't be ready",
        )
        self.assertFalse(capture.records, "trigger should has been skipped")

    def test_cron_keep_future_triggers(self):

        self.frozen_datetime.tick(delta=timedelta(days=-1))

        self.cron.active = False
        self.cron.nextcall = fields.Datetime.now() + timedelta(days=10)
        self.cron.flush_recordset()

        with self.capture_triggers() as capture:
            self.cron._trigger(at=fields.Datetime.now() + timedelta(days=1))

        self.cron.active = True
        self.cron.flush_recordset()

        self.frozen_datetime.tick(delta=timedelta(days=1))
        ready_jobs = self.registry["ir.cron"]._get_jobs_ready(self.cr)
        self.assertIn(
            self.cron.id,
            [job.id for job in ready_jobs],
            "cron should be ready",
        )
        self.assertTrue(capture.records, "trigger should has been kept")

    def test_trigger_call_at_uses_db_transaction_clock(self):
        db_time = datetime(2020, 1, 1, 12, 0, 0)
        self.patch(self.env.cr, "now", lambda: db_time)
        with self.capture_triggers(self.cron.id) as capture:
            self.cron._trigger()
        self.assertEqual(
            capture.records.call_at,
            db_time,
            "trigger call_at must come from cr.now(), not fields.Datetime.now()",
        )

    def test_toggle_sets_active_from_domain_existence(self):
        self.env["ir.config_parameter"].sudo().set_param("database.is_neutralized", "")
        self.cron.write({"active": False})
        self.cron.toggle("res.partner", [("id", "=", self.partner.id)])
        self.assertTrue(self.cron.active, "matching domain -> cron enabled")
        self.cron.toggle("res.partner", [("id", "=", 0)])
        self.assertFalse(self.cron.active, "empty domain -> cron disabled")

    def test_toggle_noop_on_neutralized_database(self):
        self.env["ir.config_parameter"].sudo().set_param("database.is_neutralized", "1")
        self.cron.write({"active": False})
        self.cron.toggle("res.partner", [("id", "=", self.partner.id)])
        self.assertFalse(
            self.cron.active, "neutralized DB -> toggle is a no-op, stays disabled"
        )

    def test_cron_process_job(self):
        Progress = self.env["ir.cron.progress"]
        ten_days_ago = (
            fields.Datetime.now() - MIN_DELTA_BEFORE_DEACTIVATION - timedelta(days=2)
        )
        almost_failed = MIN_FAILURE_COUNT_BEFORE_DEACTIVATION - 1
        frozen_datetime = self.frozen_datetime

        def nothing(cron):
            state = {"call_count": 0}

            def f(self):
                state["call_count"] += 1

            return f, state

        def eleven_success(cron):
            state = {"call_count": 0}
            CALL_TARGET = 11

            def f(self):
                frozen_datetime.tick(delta=timedelta(seconds=1))
                state["call_count"] += 1
                self.env["ir.cron"]._commit_progress(
                    processed=1, remaining=CALL_TARGET - state["call_count"]
                )

            return f, state

        def five_success(cron):
            state = {"call_count": 0}
            CALL_TARGET = 5

            def f(self):
                state["call_count"] += 1
                self.env["ir.cron"]._commit_progress(
                    processed=1, remaining=CALL_TARGET - state["call_count"]
                )

            return f, state

        def end_time(cron):
            state = {
                "call_count": 0,
                "remaining": MIN_TIME_PER_JOB + 1,
            }

            def f(self):
                state["call_count"] += 1
                while self.env["ir.cron"]._commit_progress(
                    remaining=state["remaining"]
                ):
                    state["remaining"] -= 1
                    frozen_datetime.tick(delta=timedelta(seconds=1))
                    self.env["ir.cron"]._commit_progress(1)

            return f, state

        def failure(cron):
            state = {"call_count": 0}

            def f(self):
                state["call_count"] += 1
                raise ValueError

            return f, state

        def failure_partial(cron):
            state = {"call_count": 0}
            CALL_TARGET = 5

            def f(self):
                state["call_count"] += 1
                self.env["ir.cron"]._commit_progress(
                    processed=1, remaining=CALL_TARGET - state["call_count"]
                )
                self.env.cr.commit()
                raise ValueError

            return f, state

        def failure_fully(cron):
            state = {"call_count": 0}

            def f(self):
                state["call_count"] += 1
                self.env["ir.cron"]._commit_progress(1, remaining=0)
                self.env.cr.commit()
                raise ValueError

            return f, state

        CASES = [
            (nothing, 0, False, 1, 0, 0, True),
            (nothing, almost_failed, False, 1, 0, 0, True),
            (eleven_success, 0, True, 10, 10, 0, True),
            (eleven_success, almost_failed, True, 10, 10, 0, True),
            (five_success, 0, False, 5, 5, 0, True),
            (five_success, almost_failed, False, 5, 5, 0, True),
            (end_time, 0, True, 2, 10, 0, True),
            (failure, 0, False, 1, 0, 1, True),
            (failure, almost_failed, False, 1, 0, 0, False),
            (failure_partial, 0, False, 5, 5, 1, True),
            (failure_partial, almost_failed, False, 5, 5, 0, False),
            (failure_fully, 0, False, 1, 1, 1, True),
            (failure_fully, almost_failed, False, 1, 1, 0, False),
        ]

        for (
            cb,
            curr_failures,
            trigger,
            call_count,
            done_count,
            fail_count,
            active,
        ) in CASES:
            with (
                self.subTest(cb=cb, failure=curr_failures),
                closing(self.cr.savepoint()),
            ):
                self.cron.write(
                    {
                        "active": True,
                        "failure_count": curr_failures,
                        "first_failure_date": (ten_days_ago if curr_failures else None),
                    }
                )
                with self.capture_triggers(self.cron.id) as capture:
                    if trigger:
                        self.cron._trigger()

                self.env.flush_all()
                with self.enter_registry_test_mode():
                    cb, state = cb(self.cron)
                    with (
                        mute_logger("odoo.addons.base.models.ir_cron"),
                        patch.object(self.registry["ir.actions.server"], "run", cb),
                        self.registry.cursor() as cr,
                    ):
                        self.registry["ir.cron"]._run_job(cr, self._acquire_job(cr))
                self.cron.invalidate_recordset()
                capture.records.invalidate_recordset()

                self.assertEqual(
                    self.cron.id
                    in [job.id for job in self.cron._get_jobs_ready(self.env.cr)],
                    trigger,
                )
                self.assertEqual(state["call_count"], call_count)
                self.assertEqual(
                    sum(
                        Progress.search(
                            [("cron_id", "=", self.cron.id), ("done", ">=", 1)]
                        ).mapped("done")
                    ),
                    done_count,
                )
                self.assertEqual(self.cron.failure_count, fail_count)
                self.assertEqual(self.cron.active, active)

    def test_cron_retrigger(self):
        Trigger = self.env["ir.cron.trigger"]
        Progress = self.env["ir.cron.progress"]
        frozen_datetime = self.frozen_datetime

        CALL_TARGET = 31
        mocked_run_state = {"call_count": 0, "duration": 0}

        def mocked_run(self):
            frozen_datetime.tick(delta=timedelta(seconds=mocked_run_state["duration"]))
            mocked_run_state["call_count"] += 1
            self.env["ir.cron"]._commit_progress(
                processed=1,
                remaining=CALL_TARGET - mocked_run_state["call_count"],
            )

        self.cron._trigger()
        self.env.flush_all()
        with (
            self.enter_registry_test_mode(),
            patch.object(self.registry["ir.actions.server"], "run", mocked_run),
            self.registry.cursor() as cr,
        ):
            mocked_run_state["duration"] = 2
            self.registry["ir.cron"]._run_job(cr, self._acquire_job(cr))

        self.assertEqual(
            mocked_run_state["call_count"],
            10,
            "`run` should have been called 10 times",
        )
        domain = [("cron_id", "=", self.cron.id)]
        self.assertEqual(
            Progress.search_count(domain),
            1,
            "one progress row per run, not one per attempt",
        )
        self.assertEqual(
            sum(Progress.search(domain).mapped("done")),
            10,
            "and it carries what the run actually processed",
        )
        self.assertEqual(
            Trigger.search_count([("cron_id", "=", self.cron.id)]),
            1,
            "One trigger should have been kept",
        )

        self.env.flush_all()
        with (
            self.enter_registry_test_mode(),
            patch.object(self.registry["ir.actions.server"], "run", mocked_run),
            self.registry.cursor() as cr,
        ):
            mocked_run_state["duration"] = 0.5
            self.registry["ir.cron"]._run_job(cr, self._acquire_job(cr))

        self.assertEqual(
            mocked_run_state["call_count"],
            30,
            "`run` should have been called 10 times",
        )
        self.assertEqual(
            Progress.search_count(domain),
            2,
            "the second run gets its own row",
        )
        self.assertEqual(
            sum(Progress.search(domain).mapped("done")),
            30,
            "10 from the first run and 20 from the second",
        )
        self.assertEqual(
            Trigger.search_count([("cron_id", "=", self.cron.id)]),
            1,
            "One trigger should have been kept",
        )

        self.env.flush_all()
        with (
            self.enter_registry_test_mode(),
            patch.object(self.registry["ir.actions.server"], "run", mocked_run),
            self.registry.cursor() as cr,
        ):
            self.registry["ir.cron"]._run_job(cr, self._acquire_job(cr))

        ready_jobs = self.registry["ir.cron"]._get_jobs_ready(self.cr)
        self.assertNotIn(
            self.cron.id,
            [job.id for job in ready_jobs],
            "The cron has finished executing",
        )
        self.assertEqual(
            mocked_run_state["call_count"],
            31,
            "`run` should have been called one additional time",
        )
        self.assertEqual(
            Progress.search_count(domain),
            3,
            "three runs, three rows",
        )
        self.assertEqual(
            sum(Progress.search(domain).mapped("done")),
            31,
            "and 31 records processed across them",
        )

    def test_cron_failed_increase(self):
        self.cron._trigger()
        self.env.flush_all()
        with self.enter_registry_test_mode():
            with (
                patch.object(
                    self.registry["ir.cron"],
                    "_run_server_action",
                    side_effect=Exception,
                ),
                patch.object(self.registry["ir.cron"], "_notify_admin") as notify,
                mute_logger("odoo.addons.base.models.ir_cron"),
                self.registry.cursor() as cr,
            ):
                self.registry["ir.cron"]._run_job(cr, self._acquire_job(cr))

        self.env.invalidate_all()
        self.assertEqual(self.cron.failure_count, 1, "The cron should have failed once")
        self.assertEqual(self.cron.active, True, "The cron should still be active")
        self.assertFalse(notify.called)

        self.cron.failure_count = 4

        self.cron._trigger()
        self.env.flush_all()
        with (
            self.enter_registry_test_mode(),
            patch.object(
                self.registry["ir.cron"], "_run_server_action", side_effect=Exception
            ),
            patch.object(self.registry["ir.cron"], "_notify_admin") as notify,
            mute_logger("odoo.addons.base.models.ir_cron"),
            self.registry.cursor() as cr,
        ):
            self.registry["ir.cron"]._run_job(cr, self._acquire_job(cr))

        self.env.invalidate_all()
        self.assertEqual(
            self.cron.failure_count,
            5,
            "The cron should have failed one more time but not reset (due to time)",
        )
        self.assertEqual(
            self.cron.active,
            True,
            "The cron should not have been deactivated due to time constraint",
        )
        self.assertFalse(notify.called)

        self.cron.failure_count = 4
        self.cron.first_failure_date = fields.Datetime.now() - timedelta(days=8)

        self.cron._trigger()
        self.env.flush_all()
        with (
            self.enter_registry_test_mode(),
            patch.object(
                self.registry["ir.cron"], "_run_server_action", side_effect=Exception
            ),
            patch.object(self.registry["ir.cron"], "_notify_admin") as notify,
            mute_logger("odoo.addons.base.models.ir_cron"),
            self.registry.cursor() as cr,
        ):
            self.registry["ir.cron"]._run_job(cr, self._acquire_job(cr))

        self.env.invalidate_all()
        self.assertEqual(
            self.cron.failure_count,
            0,
            "The cron should have failed one more time and reset to 0",
        )
        self.assertEqual(
            self.cron.active,
            False,
            "The cron should have been deactivated after 5 failures",
        )
        self.assertTrue(notify.called)

    def test_cron_timeout_failure(self):
        self.cron._trigger()
        self.env["ir.cron.progress"].create(
            [
                {
                    "cron_id": self.cron.id,
                    "remaining": 0,
                    "done": 0,
                    "timed_out_counter": 3,
                }
            ]
        )
        self.env.flush_all()
        with (
            self.enter_registry_test_mode(),
            mute_logger("odoo.addons.base.models.ir_cron"),
            self.registry.cursor() as cr,
        ):
            self.registry["ir.cron"]._run_job(cr, self._acquire_job(cr))

        self.env.invalidate_all()
        self.assertEqual(self.cron.failure_count, 1, "The cron should have failed once")
        self.assertEqual(self.cron.active, True, "The cron should still be active")

        self.cron._trigger()
        with self.enter_registry_test_mode(), self.registry.cursor() as cr:
            self.registry["ir.cron"]._run_job(cr, self._acquire_job(cr))

        self.env.invalidate_all()
        self.assertEqual(
            self.cron.failure_count,
            0,
            "The cron should have succeeded and reset the counter",
        )

    def test_cron_timeout_failure_after_recorded_progress(self):
        calls = {"n": 0}

        def mocked_run(self):
            calls["n"] += 1
            self.env["ir.cron"]._commit_progress(processed=1, remaining=5)

        self.cron._trigger()
        self.env["ir.cron.progress"].create(
            [
                {
                    "cron_id": self.cron.id,
                    "remaining": 5,
                    "done": 5,
                    "timed_out_counter": CONSECUTIVE_TIMEOUT_FOR_FAILURE,
                }
            ]
        )
        self.env.flush_all()
        with (
            self.enter_registry_test_mode(),
            mute_logger("odoo.addons.base.models.ir_cron"),
            patch.object(self.registry["ir.actions.server"], "run", mocked_run),
            self.registry.cursor() as cr,
        ):
            self.registry["ir.cron"]._run_job(cr, self._acquire_job(cr))

        self.assertEqual(
            calls["n"],
            0,
            "a job killed CONSECUTIVE_TIMEOUT_FOR_FAILURE times running is a hang; "
            "having committed a record before each kill does not make it healthy",
        )
        self.env.invalidate_all()
        self.assertEqual(self.cron.failure_count, 1, "The cron should have failed once")
        self.assertEqual(self.cron.active, True, "The cron should still be active")

    def test_acquire_processed_job(self):
        job = self.env["ir.cron"]._acquire_job(self.cr, self.cron.id)
        self.assertEqual(
            job, None, "No error should be thrown, job should just be none"
        )

    @contextlib.contextmanager
    def patch_cron_run_jobs_until_deadline(self):
        self.cron.active = True
        self.cron.search([("id", "not in", self.cron.ids)]).active = False
        with (
            self.enter_registry_test_mode(),
            self.registry.cursor() as cr,
        ):

            def process_jobs(**kw):
                kw.setdefault("job_ids", self.cron.ids)
                return IrCron._run_jobs_until_deadline(cr, **kw)

            yield process_jobs

    def patch_run_job(self, return_value=CompletionStatus.FULLY_DONE):
        return patch.object(
            self.registry["ir.cron"],
            "_run_job_within_budget",
            return_value=return_value,
        )

    def test_cron_process_jobs_simple(self):
        with (
            self.patch_cron_run_jobs_until_deadline() as process_jobs,
            self.patch_run_job() as run,
        ):
            cron = self.cron.create(self._get_cron_data(self.env))
            cron._trigger()
            self.cron._trigger()
            job_ids = cron.ids + self.cron.ids
            process_jobs(job_ids=job_ids)
            self.assertTrue(
                all(
                    any(job_id == call.args[0].id for call in run.mock_calls)
                    for job_id in job_ids
                ),
                "all jobs called at least once",
            )

    def test_cron_process_jobs_status_partial(self):
        with (
            self.patch_cron_run_jobs_until_deadline() as process_jobs,
            self.patch_run_job(CompletionStatus.PARTIALLY_DONE) as run,
        ):
            self.cron._trigger()
            process_jobs()
            run.assert_called_once()

    def test_cron_process_jobs_status_failed(self):
        with (
            self.patch_cron_run_jobs_until_deadline() as process_jobs,
            self.patch_run_job(CompletionStatus.FAILED) as run,
        ):
            self.cron._trigger()
            process_jobs()
            run.assert_called_once()

    def test_cron_pass_stops_on_its_deadline_instead_of_being_killed(self):
        with (
            self.patch_cron_run_jobs_until_deadline() as process_jobs,
            self.patch_run_job() as run,
            patch.object(ir_cron, "notify_channel") as notify,
        ):
            other = self.cron.create(self._get_cron_data(self.env))
            job_ids = self.cron.ids + other.ids
            self.cron._trigger()
            other._trigger()
            yielded = process_jobs(job_ids=job_ids, deadline=time.monotonic() - 1)
        self.assertTrue(yielded, "it reports that ready crons remain")
        run.assert_not_called()
        notify.assert_called_once()
        self.assertEqual(notify.call_args.args[1], self.env.cr.dbname)

    def test_cron_pass_within_its_deadline_runs_every_ready_cron(self):
        deadline = time.monotonic() + 300
        with (
            self.patch_cron_run_jobs_until_deadline() as process_jobs,
            self.patch_run_job() as run,
        ):
            other = self.cron.create(self._get_cron_data(self.env))
            self.cron._trigger()
            other._trigger()
            yielded = process_jobs(job_ids=self.cron.ids + other.ids, deadline=deadline)
        self.assertFalse(yielded)
        self.assertEqual(run.call_count, 2)
        for call in run.mock_calls:
            self.assertEqual(call.kwargs["deadline"], deadline)

    def test_deferred_crons_are_reached_by_the_following_passes(self):
        with (
            self.patch_cron_run_jobs_until_deadline() as process_jobs,
            patch.object(ir_cron, "notify_channel"),
        ):
            crons = self.cron
            for _ in range(3):
                crons |= self.cron.create(self._get_cron_data(self.env))
            crons.write({"nextcall": fields.Datetime.now()})
            self.env.flush_all()

            ran = []
            with patch.object(
                self.registry["ir.cron"], "_run_job_within_budget"
            ) as run:
                run.return_value = CompletionStatus.FULLY_DONE
                run.side_effect = lambda job, **kw: (
                    ran.append(job.id),
                    CompletionStatus.FULLY_DONE,
                )[1]
                for _pass in range(4):
                    ready = self.registry["ir.cron"]._get_jobs_ready(self.cr)
                    ready_ids = [job.id for job in ready if job.id in crons.ids]
                    if not ready_ids:
                        break
                    process_jobs(
                        job_ids=ready_ids,
                        deadline=time.monotonic() + (0.05 if _pass else -1),
                    )
        self.assertEqual(
            set(ran), set(crons.ids), "every deferred cron was reached in the end"
        )

    def test_cron_process_jobs_locked(self):
        with (
            self.patch_cron_run_jobs_until_deadline() as process_jobs,
            self.patch_run_job() as run,
            patch.object(IrCron, "_acquire_job", return_value=None) as acquire,
            patch.object(time, "monotonic", side_effect=lambda: 42 + run.call_count),
        ):
            self.cron._trigger()
            process_jobs()
            run.assert_not_called()
            acquire.assert_called_once()

    def test_cron_commit_progress(self):
        with self.enter_registry_test_mode(), self.registry.cursor() as cr:
            cron = self.cron.with_env(
                self.cron.env(cr=cr, context={"cron_id": self.cron.id})
            )

            cron, progress = cron._add_progress()
            result = cron._commit_progress()
            self.assertEqual(result, float("inf"))
            result = cron.with_context(
                cron_end_time=time.monotonic() - 1
            )._commit_progress()
            self.assertEqual(result, 0)

            cron, progress = cron._add_progress()
            cron._commit_progress(remaining=5)
            self.assertEqual(progress.done, 0)
            self.assertEqual(progress.remaining, 5)
            cron._commit_progress(processed=3, remaining=7)
            self.assertEqual(progress.done, 3)
            self.assertEqual(progress.remaining, 7)

            cron, progress = cron._add_progress()
            cron._commit_progress(remaining=5)
            cron._commit_progress(2)
            self.assertEqual(progress.done, 2)
            self.assertEqual(progress.remaining, 3)
            cron._commit_progress(2)
            self.assertEqual(progress.done, 4)
            self.assertEqual(progress.remaining, 1)
            cron._commit_progress(2)
            self.assertEqual(progress.done, 6)
            self.assertEqual(progress.remaining, 0)

            cron, progress = cron._add_progress()
            cron._commit_progress(1, deactivate=True)
            self.assertEqual(progress.done, 1)
            self.assertEqual(progress.deactivate, True)
            cron._commit_progress(1)
            self.assertEqual(progress.done, 2)
            self.assertEqual(progress.deactivate, True)

    def test_cron_deactivate(self):
        def mocked_run(self):
            self.env["ir.cron"]._commit_progress(
                processed=1, remaining=0, deactivate=True
            )

        self.cron._trigger()
        self.env.flush_all()
        with (
            self.enter_registry_test_mode(),
            patch.object(self.registry["ir.actions.server"], "run", mocked_run),
            self.registry.cursor() as cr,
        ):
            self.registry["ir.cron"]._run_job(cr, self._acquire_job(cr))

        self.env.invalidate_all()
        self.assertFalse(self.cron.active)

    def test_cron_deactivate_production_shape(self):

        def mocked_run(self):
            self.env["ir.cron"]._commit_progress(
                processed=1, remaining=0, deactivate=True
            )

        self.cron._trigger()
        self.env.flush_all()
        with (
            self.enter_registry_test_mode(),
            patch.object(self.registry["ir.actions.server"], "run", mocked_run),
            self.registry.cursor() as cr,
        ):
            job = self._acquire_job(cr)
            self.assertEqual(job.failure_count, 0)
            self.assertIsNone(
                job.first_failure_date,
                "NULL must surface as None, as dictfetchone yields it",
            )
            self.assertTrue(job.active)
            self.registry["ir.cron"]._run_job(cr, job)

        self.env.cr.execute("SELECT active FROM ir_cron WHERE id = %s", [self.cron.id])
        self.assertFalse(
            self.env.cr.fetchone()[0],
            "the deactivation requested via _commit_progress(deactivate=True) "
            "must reach the database",
        )

    def test_gc_cron_triggers_uses_transaction_clock(self):
        self.cron.active = False
        trigger = self.env["ir.cron.trigger"].create(
            {"cron_id": self.cron.id, "call_at": fields.Datetime.now()}
        )
        self.env.flush_all()
        db_future = trigger.call_at + TRIGGER_RETENTION_PERIOD + timedelta(days=1)
        self.patch(self.env.cr, "now", lambda: db_future)
        self.env["ir.cron.trigger"]._gc_cron_triggers()
        self.assertFalse(
            trigger.exists(),
            "GC must follow the transaction clock, not the process wall clock",
        )

    def test_gc_cron_progress_uses_transaction_clock(self):
        old, recent = self.env["ir.cron.progress"].create(
            [
                {"cron_id": self.cron.id, "remaining": 0, "done": 0},
                {"cron_id": self.cron.id, "remaining": 0, "done": 0},
            ]
        )
        self.env.flush_all()
        db_future = old.create_date + PROGRESS_RETENTION_PERIOD + timedelta(days=1)
        self.patch(self.env.cr, "now", lambda: db_future)
        self.env["ir.cron.progress"]._gc_cron_progress()
        self.assertFalse(
            old.exists(),
            "GC must follow the transaction clock, not the process wall clock",
        )
        self.assertTrue(recent.exists())

    def test_gc_cron_progress_keeps_the_latest_row_of_each_cron(self):
        other = self.env["ir.cron"].create(self._get_cron_data(self.env))
        older, newer, lone = self.env["ir.cron.progress"].create(
            [
                {"cron_id": other.id, "timed_out_counter": 1},
                {"cron_id": other.id, "timed_out_counter": 2},
                {"cron_id": self.cron.id, "timed_out_counter": 2},
            ]
        )
        self.env.flush_all()
        db_future = lone.create_date + PROGRESS_RETENTION_PERIOD + timedelta(days=1)
        self.patch(self.env.cr, "now", lambda: db_future)
        self.env["ir.cron.progress"]._gc_cron_progress()
        self.env.invalidate_all()
        self.assertFalse(
            older.exists(), "a superseded row past the retention period must go"
        )
        self.assertTrue(
            newer.exists(),
            "but never the newest row of a cron: _acquire_job reads exactly that "
            "one for done/remaining/timed_out_counter",
        )
        self.assertTrue(lone.exists(), "a cron whose only row is old still keeps it")


class TestIrCronUser(TransactionCaseWithUserDemo, TestIrCron):
    def test_cron_archived_admin_user(self):
        cron_data = self._get_cron_data(self.env)
        cron_data["user_id"] = self.user_demo.id

        user = self.env["res.users"].browse(cron_data["user_id"])
        user.active = False
        user.group_ids += self.env.ref("base.group_system")
        cron = self.cron.create(cron_data)

        cron._trigger()
        self.env.flush_all()
        with self.enter_registry_test_mode(), self.registry.cursor() as cr:
            with self.assertLogs(
                "odoo.addons.base.models.ir_cron", level="WARNING"
            ) as log_catcher:
                self.registry["ir.cron"]._run_job(cr, self._acquire_job(cr, cron))
                self.assertEqual(
                    [
                        Like(
                            f"...Forbidden server action '{cron.name}' executed while the user {user.login} is archived..."
                        )
                    ],
                    log_catcher.output,
                )

        self.assertEqual(cron.failure_count, 1, "The cron should have failed once")


@tagged("post_install", "-at_install")
class TestNotifyChannelIsBestEffort(BaseCase):
    def test_a_database_error_does_not_reach_the_caller(self):
        with (
            patch.object(ir_cron.db, "db_connect") as connect,
            self.assertLogs("odoo.addons.base.models.ir_cron", "WARNING") as logs,
        ):
            connect.side_effect = psycopg.OperationalError(
                "FATAL:  sorry, too many clients already"
            )
            ir_cron.notify_channel(CRON_TRIGGER_CHANNEL, "somedb")
        self.assertIn("Could not notify", logs.output[0])

    def test_a_non_database_error_still_propagates(self):
        with patch.object(ir_cron.db, "db_connect") as connect:
            connect.side_effect = TypeError("a bug in this function, not the cluster")
            with self.assertRaises(TypeError):
                ir_cron.notify_channel(CRON_TRIGGER_CHANNEL, "somedb")


@tagged("post_install", "-at_install")
class TestIrCronAcquireLock(BaseCase):
    def setUp(self):
        super().setUp()
        self.registry = Registry(common.get_db_name())
        with self.registry.cursor() as cr:
            env = odoo.api.Environment(cr, common.ADMIN_USER_ID, {})
            cron = env["ir.cron"].create(
                {
                    "name": f"Audit lock cron {secrets.token_urlsafe(8)}",
                    "state": "code",
                    "code": "",
                    "model_id": env.ref("base.model_res_partner").id,
                    "user_id": env.uid,
                    "active": True,
                    "repeat_interval": 1,
                    "repeat_unit": "day",
                    "nextcall": datetime(2000, 1, 1, 0, 0, 0),
                }
            )
            self.cron_id = cron.id
            cr.commit()
        self.addCleanup(self._drop_cron)

    def _drop_cron(self):
        with self.registry.cursor() as cr:
            env = odoo.api.Environment(cr, common.ADMIN_USER_ID, {})
            env["ir.cron"].browse(self.cron_id).unlink()
            cr.commit()

    def test_acquire_job_skips_locked_row(self):
        IrCronModel = self.registry["ir.cron"]
        with self.registry.cursor() as cr_a, self.registry.cursor() as cr_b:
            job_a = IrCronModel._acquire_job(cr_a, self.cron_id)
            self.assertIsNotNone(job_a, "connection A should acquire the ready job")
            self.assertEqual(job_a.id, self.cron_id)

            job_b = IrCronModel._acquire_job(cr_b, self.cron_id)
            self.assertIsNone(
                job_b,
                "connection B must skip the row locked by connection A",
            )

            cr_a.rollback()
            cr_b.rollback()

    def test_acquire_job_after_release(self):
        IrCronModel = self.registry["ir.cron"]
        with self.registry.cursor() as cr_a:
            job_a = IrCronModel._acquire_job(cr_a, self.cron_id)
            self.assertIsNotNone(job_a)
            cr_a.commit()

        with self.registry.cursor() as cr_b:
            job_b = IrCronModel._acquire_job(cr_b, self.cron_id)
            self.assertIsNotNone(
                job_b,
                "the job must be acquirable again once the lock is released",
            )
            self.assertEqual(job_b.id, self.cron_id)
            cr_b.rollback()

    def test_write_on_running_cron_raises_usererror(self):
        IrCronModel = self.registry["ir.cron"]
        with self.registry.cursor() as cr_a, self.registry.cursor() as cr_b:
            job_a = IrCronModel._acquire_job(cr_a, self.cron_id)
            self.assertIsNotNone(job_a, "connection A should hold the lock")

            env_b = odoo.api.Environment(cr_b, common.ADMIN_USER_ID, {})
            with self.assertRaises(UserError) as cm:
                env_b["ir.cron"].browse(self.cron_id).write({"priority": 3})
            self.assertIn("currently being executed", str(cm.exception))

            cr_a.rollback()
            cr_b.rollback()

    def test_unlink_on_running_cron_raises_usererror(self):
        IrCronModel = self.registry["ir.cron"]
        with self.registry.cursor() as cr_a, self.registry.cursor() as cr_b:
            job_a = IrCronModel._acquire_job(cr_a, self.cron_id)
            self.assertIsNotNone(job_a, "connection A should hold the lock")

            env_b = odoo.api.Environment(cr_b, common.ADMIN_USER_ID, {})
            with self.assertRaises(UserError) as cm:
                env_b["ir.cron"].browse(self.cron_id).unlink()
            self.assertIn("currently being executed", str(cm.exception))

            cr_a.rollback()
            cr_b.rollback()


class TestIrCronClassifyOutcome(BaseCase):
    def test_resolve_completion_status_full_truth_table(self):
        FD = CompletionStatus.FULLY_DONE
        PD = CompletionStatus.PARTIALLY_DONE
        FL = CompletionStatus.FAILED
        cases = {
            (False, 0, 0): FL,
            (False, 0, 5): FL,
            (False, 3, 0): FL,
            (False, 3, 5): None,
            (True, 0, 0): FD,
            (True, 3, 0): FD,
            (True, 0, 5): PD,
            (True, 3, 5): None,
        }
        for (success, done, remaining), expected in cases.items():
            with self.subTest(success=success, done=done, remaining=remaining):
                self.assertEqual(
                    IrCron._resolve_completion_status(
                        success=success, done=done, remaining=remaining
                    ),
                    expected,
                )

    def test_resolve_completion_status_ignores_magnitude(self):
        self.assertEqual(
            IrCron._resolve_completion_status(success=True, done=999, remaining=0),
            CompletionStatus.FULLY_DONE,
        )
        self.assertEqual(
            IrCron._resolve_completion_status(success=True, done=1, remaining=1),
            IrCron._resolve_completion_status(success=True, done=1000, remaining=1000),
        )


class TestIrCronComputeNextCall(TransactionCase):
    def _rec(self, tz):
        return self.env["ir.cron"].with_context(tz=tz)

    def test_utc_daily_plain_advance(self):
        rec = self._rec("UTC")
        nextcall = IrCron._get_next_call(
            rec, datetime(2026, 1, 1, 0, 0), datetime(2026, 1, 3, 12, 0), "day", 1
        )
        self.assertEqual(nextcall, datetime(2026, 1, 4, 0, 0))

    def test_daily_keeps_wall_clock_hour_across_spring_forward(self):
        rec = self._rec("America/New_York")
        nextcall = IrCron._get_next_call(
            rec,
            datetime(2026, 3, 7, 12, 0),
            datetime(2026, 3, 9, 6, 0),
            "day",
            1,
        )
        self.assertEqual(nextcall, datetime(2026, 3, 9, 11, 0))
        local = fields.Datetime.context_timestamp(rec, nextcall)
        self.assertEqual(local.hour, 7, "local wall-clock hour must be preserved")

    def test_daily_keeps_wall_clock_hour_across_fall_back(self):
        rec = self._rec("America/New_York")
        nextcall = IrCron._get_next_call(
            rec,
            datetime(2026, 10, 31, 11, 0),
            datetime(2026, 11, 2, 6, 0),
            "day",
            1,
        )
        self.assertEqual(nextcall, datetime(2026, 11, 2, 12, 0))
        local = fields.Datetime.context_timestamp(rec, nextcall)
        self.assertEqual(local.hour, 7, "local wall-clock hour must be preserved")

    def test_result_is_strictly_after_now_for_all_units(self):
        rec = self._rec("Europe/Brussels")
        now = datetime(2026, 6, 15, 12, 0)
        overdue = now - timedelta(days=400)
        for unit in ("minute", "hour", "day", "week", "month"):
            with self.subTest(unit=unit):
                nextcall = IrCron._get_next_call(rec, overdue, now, unit, 1)
                self.assertGreater(nextcall, now)

    def test_fixed_interval_catchup_matches_stepwise_loop(self):
        rec = self._rec("America/New_York")
        now = datetime(2026, 6, 15, 12, 0)
        for unit, interval, overdue in [
            ("minute", 1, timedelta(hours=3)),
            ("minute", 7, timedelta(days=2, minutes=3)),
            ("minute", 30, timedelta(seconds=1)),
            ("hour", 1, timedelta(days=5, minutes=30)),
            ("hour", 6, timedelta(days=1)),
        ]:
            with self.subTest(unit=unit, n=interval):
                nextcall = now - overdue
                expected = nextcall
                step = timedelta(**{f"{unit}s": interval})
                while expected <= now:
                    expected += step
                self.assertEqual(
                    IrCron._get_next_call(rec, nextcall, now, unit, interval),
                    expected,
                )

    def test_fixed_interval_boundary_nextcall_equals_now_advances_once(self):
        rec = self._rec("UTC")
        now = datetime(2026, 6, 15, 12, 0)
        for unit in ("minute", "hour"):
            with self.subTest(unit=unit):
                self.assertEqual(
                    IrCron._get_next_call(rec, now, now, unit, 5),
                    now + timedelta(**{f"{unit}s": 5}),
                )

    def test_fixed_interval_future_nextcall_unchanged(self):
        rec = self._rec("UTC")
        now = datetime(2026, 6, 15, 12, 0)
        future = now + timedelta(seconds=1)
        self.assertEqual(IrCron._get_next_call(rec, future, now, "minute", 5), future)

    def test_fixed_interval_long_overdue_catchup(self):
        rec = self._rec("UTC")
        now = datetime(2026, 6, 15, 12, 0, 30)
        nextcall = now - timedelta(days=400)
        self.assertEqual(
            IrCron._get_next_call(rec, nextcall, now, "minute", 1),
            datetime(2026, 6, 15, 12, 1, 30),
        )


class TestIrCronCanKeepRunning(BaseCase):
    def test_terminal_status_stops_immediately(self):
        for status in CompletionStatus:
            with self.subTest(status=status):
                self.assertFalse(
                    IrCron._can_keep_running(
                        status=status, loop_count=0, now=0.0, end_time=1e9
                    )
                )

    def test_under_min_runs_continues_even_with_no_time_left(self):
        self.assertTrue(
            IrCron._can_keep_running(
                status=None, loop_count=MIN_RUNS_PER_JOB - 1, now=100.0, end_time=0.0
            )
        )

    def test_min_runs_reached_and_time_spent_stops(self):
        self.assertFalse(
            IrCron._can_keep_running(
                status=None, loop_count=MIN_RUNS_PER_JOB, now=100.0, end_time=100.0
            )
        )

    def test_min_runs_reached_but_time_left_continues(self):
        self.assertTrue(
            IrCron._can_keep_running(
                status=None,
                loop_count=MIN_RUNS_PER_JOB + 5,
                now=50.0,
                end_time=100.0,
            )
        )

    def test_hard_deadline_overrides_the_minimum_run_count(self):
        self.assertFalse(
            IrCron._can_keep_running(
                status=None,
                loop_count=1,
                now=100.0,
                end_time=1e9,
                hard_deadline=100.0,
            )
        )

    def test_a_spent_deadline_still_owes_the_job_its_first_pass(self):
        self.assertTrue(
            IrCron._can_keep_running(
                status=None,
                loop_count=0,
                now=100.0,
                end_time=0.0,
                hard_deadline=1.0,
            )
        )
        self.assertFalse(
            IrCron._can_keep_running(
                status=None,
                loop_count=1,
                now=100.0,
                end_time=0.0,
                hard_deadline=1.0,
            )
        )

    def test_hard_deadline_not_reached_keeps_the_previous_rule(self):
        self.assertTrue(
            IrCron._can_keep_running(
                status=None,
                loop_count=1,
                now=10.0,
                end_time=0.0,
                hard_deadline=100.0,
            )
        )

    def test_get_deadline_run_follows_the_worker_time_limit(self):
        with config.patch(limit_time_real_cron=100):
            self.assertEqual(IrCron._get_deadline_run(0.0), 100 * RUN_BUDGET_RATIO)
        with config.patch(limit_time_real_cron=-1, limit_time_real=50):
            self.assertEqual(IrCron._get_deadline_run(0.0), 50 * RUN_BUDGET_RATIO)
        with config.patch(limit_time_real_cron=0):
            self.assertIsNone(IrCron._get_deadline_run(0.0))

    def test_get_deadline_pass_follows_the_same_limit(self):
        with (
            config.patch(limit_time_real_cron=100),
            patch.object(time, "monotonic", return_value=1000.0),
        ):
            self.assertEqual(
                IrCron._get_deadline_pass(), 1000.0 + 100 * RUN_BUDGET_RATIO
            )
        with config.patch(limit_time_real_cron=0):
            self.assertIsNone(IrCron._get_deadline_pass())


class TestIrCronUpdateFailureCount(TransactionCase, CronMixinCase):
    def setUp(self):
        super().setUp()
        self.cron = self.env["ir.cron"].create(self._get_cron_data(self.env))

    def _get_now(self):
        return self.env["ir.cron"]._get_now()

    def _apply(self, status, **job_overrides):
        job = make_job(self.cron, **job_overrides)
        Cron = self.env["ir.cron"]
        Cron._write_job_row(job, Cron._prepare_failure_vals(job, status))
        self.cron.invalidate_recordset()

    def test_first_failure_sets_count_and_date(self):
        self._apply(CompletionStatus.FAILED)
        self.assertEqual(self.cron.failure_count, 1)
        self.assertEqual(self.cron.first_failure_date, self._get_now())
        self.assertTrue(self.cron.active)

    def test_failure_below_count_threshold_increments_only(self):
        old = self._get_now() - MIN_DELTA_BEFORE_DEACTIVATION - timedelta(days=1)
        self._apply(CompletionStatus.FAILED, failure_count=2, first_failure_date=old)
        self.assertEqual(self.cron.failure_count, 3)
        self.assertTrue(self.cron.active)

    def test_count_met_but_time_window_open_keeps_active(self):
        recent = self._get_now()
        self._apply(
            CompletionStatus.FAILED,
            failure_count=MIN_FAILURE_COUNT_BEFORE_DEACTIVATION - 1,
            first_failure_date=recent,
        )
        self.assertEqual(self.cron.failure_count, MIN_FAILURE_COUNT_BEFORE_DEACTIVATION)
        self.assertTrue(self.cron.active, "time window not elapsed -> stay active")

    def test_both_thresholds_met_deactivates_resets_and_notifies(self):
        old = self._get_now() - MIN_DELTA_BEFORE_DEACTIVATION - timedelta(days=1)
        with patch.object(self.registry["ir.cron"], "_notify_admin") as notify:
            self._apply(
                CompletionStatus.FAILED,
                failure_count=MIN_FAILURE_COUNT_BEFORE_DEACTIVATION - 1,
                first_failure_date=old,
            )
        self.assertFalse(self.cron.active, "both thresholds met -> deactivated")
        self.assertEqual(self.cron.failure_count, 0, "counter reset on deactivation")
        self.assertFalse(self.cron.first_failure_date)
        notify.assert_called_once()

    def test_success_resets_counter_and_date(self):
        old = self._get_now() - timedelta(days=1)
        for status in (CompletionStatus.FULLY_DONE, CompletionStatus.PARTIALLY_DONE):
            with self.subTest(status=status):
                self.cron.write(
                    {"failure_count": 3, "first_failure_date": old, "active": True}
                )
                self.cron.flush_recordset()
                self._apply(status, failure_count=3, first_failure_date=old)
                self.assertEqual(self.cron.failure_count, 0)
                self.assertFalse(self.cron.first_failure_date)
                self.assertTrue(self.cron.active)


class TestIrCronDbChecks(TransactionCase):
    def test_check_version_mismatch_raises_bad_version(self):
        with closing(self.cr.savepoint()):
            self.cr.execute(
                "UPDATE ir_module_module SET db_version = %s WHERE name = 'base'",
                ["0.0.0.0.0"],
            )
            with self.assertRaises(BadVersionError):
                IrCron._check_version(self.cr)

    def test_check_version_null_raises_bad_module_state(self):
        with closing(self.cr.savepoint()):
            self.cr.execute(
                "UPDATE ir_module_module SET db_version = NULL WHERE name = 'base'"
            )
            with self.assertRaises(BadModuleStateError):
                IrCron._check_version(self.cr)

    def test_check_version_missing_row_raises_bad_module_state(self):
        with closing(self.cr.savepoint()):
            self.cr.execute(
                "UPDATE ir_module_module SET name = 'base__hidden' WHERE name = 'base'"
            )
            with self.assertRaises(BadModuleStateError):
                IrCron._check_version(self.cr)

    def test_check_version_match_passes(self):
        IrCron._check_version(self.cr)

    def test_check_modules_state_stable_passes(self):
        with closing(self.cr.savepoint()):
            self.cr.execute(
                "UPDATE ir_module_module SET state = 'installed' WHERE state LIKE 'to %'"
            )
            IrCron._check_modules_state(self.cr, jobs=[])

    def test_check_modules_state_transient_no_jobs_raises(self):
        with closing(self.cr.savepoint()):
            self.cr.execute(
                "UPDATE ir_module_module SET state = 'to upgrade' WHERE name = 'base'"
            )
            with self.assertRaises(BadModuleStateError):
                IrCron._check_modules_state(self.cr, jobs=[])

    def test_check_modules_state_transient_recent_job_raises(self):
        recent = fields.Datetime.now()
        with closing(self.cr.savepoint()):
            self.cr.execute(
                "UPDATE ir_module_module SET state = 'to upgrade' WHERE name = 'base'"
            )
            with self.assertRaises(BadModuleStateError):
                IrCron._check_modules_state(self.cr, jobs=[ReadyJob(1, recent, recent)])

    def test_check_modules_state_transient_stale_job_forces_reset(self):
        stale = fields.Datetime.now() - MAX_FAIL_TIME - timedelta(hours=1)
        with closing(self.cr.savepoint()):
            self.cr.execute(
                "UPDATE ir_module_module SET state = 'to upgrade' WHERE name = 'base'"
            )
            with patch(
                "odoo.addons.base.models.ir_cron.reset_modules_state"
            ) as reset_mock:
                IrCron._check_modules_state(self.cr, jobs=[ReadyJob(1, stale, stale)])
            reset_mock.assert_called_once()


class TestIrCronRunLoopContract(TransactionCase, CronMixinCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.cron = cls.env["ir.cron"].create(cls._get_cron_data(cls.env))

    def _acquire(self, cr):
        self.env.flush_all()
        job = self.registry["ir.cron"]._acquire_job(
            cr, self.cron.id, include_not_ready=True
        )
        self.assertIsNotNone(job)
        return job

    def test_completion_bookkeeping_lands_on_the_job_cursor_not_the_caller(self):
        seen_cursor_ids = []
        real_write = self.registry["ir.cron"]._write_job_row

        def spying_write(self, job, vals):
            seen_cursor_ids.append(id(self.env.cr))
            return real_write(self, job, vals)

        with (
            self.enter_registry_test_mode(),
            patch.object(self.registry["ir.cron"], "_write_job_row", spying_write),
            self.registry.cursor() as cr,
        ):
            self.registry["ir.cron"]._run_job(cr, self._acquire(cr))
            self.assertEqual(
                len(seen_cursor_ids), 1, "bookkeeping must be written once"
            )
            self.assertNotEqual(
                seen_cursor_ids[0],
                id(cr),
                "the completion bookkeeping was written on cron_cr, the "
                "caller's cursor, instead of the job's own job_cr",
            )
            cr.commit()

    def test_the_job_is_told_the_budget_the_loop_will_actually_honour(self):
        reported = []

        def mocked_run(self):
            reported.append(
                self.env["ir.cron"]._commit_progress(processed=1, remaining=5)
            )

        slice_left = 0.05
        self.cron._trigger()
        self.env.flush_all()
        with (
            self.enter_registry_test_mode(),
            patch.object(self.registry["ir.actions.server"], "run", mocked_run),
            self.registry.cursor() as cr,
        ):
            self.registry["ir.cron"]._run_job(
                cr, self._acquire(cr), deadline=time.monotonic() + slice_left
            )

        self.assertTrue(reported, "the job must have run at least once")
        self.assertLessEqual(
            reported[0],
            slice_left,
            "_commit_progress is what an incremental job asks 'how long have I "
            f"got'; with {slice_left}s left in the cron pass it may not answer "
            f"with the {MIN_TIME_PER_JOB}s per-job slice",
        )

    def test_a_job_that_fails_after_progress_stops_retrying_within_one_run(self):
        calls = {"n": 0}

        def mocked_run(self):
            calls["n"] += 1
            self.env["ir.cron"]._commit_progress(processed=1, remaining=5)
            raise RuntimeError("boom after progress")

        self.cron._trigger()
        self.env.flush_all()
        with (
            self.enter_registry_test_mode(),
            mute_logger("odoo.addons.base.models.ir_cron"),
            patch.object(self.registry["ir.actions.server"], "run", mocked_run),
            self.registry.cursor() as cr,
        ):
            self.registry["ir.cron"]._run_job(cr, self._acquire(cr))

        self.assertEqual(
            calls["n"],
            MAX_STALLED_ATTEMPTS_PER_RUN + 1,
            "a job that keeps failing without shortening its queue is not "
            "making progress; replaying it for the whole per-job slice is a "
            "hot loop",
        )
        self.env.invalidate_all()
        self.assertEqual(
            self.cron.failure_count,
            1,
            "the run failed, so it must count towards deactivation",
        )
        self.assertFalse(
            self.env["ir.cron.trigger"].search([("cron_id", "=", self.cron.id)]),
            "a failed run reschedules on the interval, it does not re-queue itself",
        )

    def test_an_intermittent_failure_does_not_end_the_run(self):
        calls = {"n": 0}

        def mocked_run(self):
            calls["n"] += 1
            self.env["ir.cron"]._commit_progress(processed=1, remaining=5)
            if calls["n"] % 2:
                raise RuntimeError("every other one")

        self.cron._trigger()
        self.env.flush_all()
        with (
            self.enter_registry_test_mode(),
            mute_logger("odoo.addons.base.models.ir_cron"),
            patch.object(self.registry["ir.actions.server"], "run", mocked_run),
            self.registry.cursor() as cr,
        ):
            self.registry["ir.cron"]._run_job(
                cr, self._acquire(cr), deadline=time.monotonic() + 0.2
            )

        self.assertGreater(
            calls["n"],
            4,
            "a failure between two good passes is not a stuck job; only a "
            "failure that leaves the queue no shorter ends the run",
        )

    def test_triggering_a_cron_many_times_notifies_the_channel_once(self):
        sent = []
        before = len(self.env.cr.postcommit)
        for _ in range(10):
            self.cron._trigger()
        self.assertEqual(
            len(self.env.cr.postcommit) - before,
            1,
            "every NOTIFY opens a connection to the maintenance database and "
            "carries the same payload; one per transaction is enough",
        )
        with patch.object(
            ir_cron,
            "notify_channel",
            lambda channel, db_name: sent.append((channel, db_name)),
        ):
            self.env.cr.postcommit.run()
        self.assertEqual(
            sent,
            [(CRON_TRIGGER_CHANNEL, self.env.cr.dbname)],
            "and the one that survives must still carry channel and database",
        )

    def test_the_run_loop_does_not_open_a_connection_just_to_check_signaling(self):
        def mocked_run(self):
            self.env["ir.cron"]._commit_progress(processed=1, remaining=0)

        self.cron._trigger()
        self.env.flush_all()
        with (
            self.enter_registry_test_mode(),
            patch.object(self.registry["ir.actions.server"], "run", mocked_run),
            self.registry.cursor() as cr,
        ):
            self.registry["ir.cron"]._run_job(cr, self._acquire(cr))
            calls = self.registry.check_signaling.call_args_list

            self.assertTrue(calls, "the run loop must still check signaling")
            passed = [call.args[0] if call.args else None for call in calls]
            self.assertTrue(
                all(cursor is not None for cursor in passed),
                "the loop already holds a cursor for every iteration; borrowing "
                "a second one from the pool to read two sequences is what "
                "starves db_maxconn",
            )
            self.assertTrue(
                all(cursor is not cr for cursor in passed),
                "it must be the job cursor, which _add_progress commits right "
                "before the check; cursors are REPEATABLE READ, so reading the "
                "sequences on a cursor mid-transaction would pin them to a "
                "snapshot taken before the reload was signalled",
            )

    def test_a_trigger_that_made_the_job_ready_does_not_survive_the_run(self):
        stamp = datetime(2026, 1, 1, 12, 0, 0, 500000)
        self.patch(self.env.cr, "now", lambda: stamp)
        trigger = self.env["ir.cron.trigger"].create(
            {
                "cron_id": self.cron.id,
                "call_at": stamp - timedelta(microseconds=1),
            }
        )
        self.env.flush_all()
        ready = self.registry["ir.cron"]._get_jobs_ready(self.env.cr)
        self.assertIn(
            self.cron.id,
            [job.id for job in ready],
            "the trigger is due, so the job is ready",
        )
        self.env["ir.cron"]._remove_triggers_due(make_job(self.cron))
        self.assertFalse(
            trigger.exists(),
            "the delete window and the readiness window must be the same clock, "
            "or the trigger fires the job a second time on the next pass",
        )

    def test_a_deactivate_asked_for_early_in_a_run_still_takes_effect(self):
        state = {"n": 0}

        def mocked_run(self):
            state["n"] += 1
            Cron = self.env["ir.cron"]
            if state["n"] == 1:
                Cron._commit_progress(processed=1, remaining=2, deactivate=True)
            else:
                Cron._commit_progress(processed=1, remaining=max(3 - state["n"], 0))

        self.cron._trigger()
        self.env.flush_all()
        with (
            self.enter_registry_test_mode(),
            patch.object(self.registry["ir.actions.server"], "run", mocked_run),
            self.registry.cursor() as cr,
        ):
            self.registry["ir.cron"]._run_job(
                cr, self._acquire(cr), deadline=time.monotonic() + 5
            )

        self.assertGreater(state["n"], 1, "the run must span several attempts")
        self.env.invalidate_all()
        self.assertFalse(
            self.cron.active,
            "a job that asked to be switched off is switched off; the request "
            "must not depend on which attempt of the run made it",
        )

    def test_a_run_leaves_one_progress_row_carrying_its_total(self):
        def mocked_run(self):
            self.env["ir.cron"]._commit_progress(processed=2, remaining=0)

        self.cron._trigger()
        self.env.flush_all()
        with (
            self.enter_registry_test_mode(),
            patch.object(self.registry["ir.actions.server"], "run", mocked_run),
            self.registry.cursor() as cr,
        ):
            self.registry["ir.cron"]._run_job(cr, self._acquire(cr))

        rows = self.env["ir.cron.progress"].search([("cron_id", "=", self.cron.id)])
        self.assertEqual(len(rows), 1, "one row per run, not one per attempt")
        self.assertEqual(rows.done, 2)

    def _count_attempts(self, *, slice_seconds, deadline_seconds, per_attempt):
        state = {"n": 0}

        def mocked_run(self):
            state["n"] += 1
            time.sleep(per_attempt)
            self.env["ir.cron"]._commit_progress(processed=1, remaining=99)

        self.cron._trigger()
        self.env.flush_all()
        with (
            self.enter_registry_test_mode(),
            patch.object(ir_cron, "MIN_TIME_PER_JOB", slice_seconds),
            patch.object(self.registry["ir.actions.server"], "run", mocked_run),
            self.registry.cursor() as cr,
        ):
            deadline = (
                None
                if deadline_seconds is None
                else time.monotonic() + deadline_seconds
            )
            self.registry["ir.cron"]._run_job(cr, self._acquire(cr), deadline=deadline)
        return state["n"]

    def test_the_slice_the_run_count_and_the_pass_deadline_compose(self):
        self.assertEqual(
            self._count_attempts(
                slice_seconds=0.1, deadline_seconds=60, per_attempt=0.02
            ),
            MIN_RUNS_PER_JOB,
            "a job whose attempts are quicker than the slice still gets its "
            "minimum count, even though the slice ran out first",
        )
        self.assertGreater(
            self._count_attempts(
                slice_seconds=1, deadline_seconds=60, per_attempt=0.02
            ),
            MIN_RUNS_PER_JOB,
            "and a job with a slice left over keeps going past that minimum: "
            "the two are a floor and a floor, not a floor and a ceiling",
        )
        self.assertLess(
            self._count_attempts(
                slice_seconds=0.1, deadline_seconds=0.05, per_attempt=0.02
            ),
            MIN_RUNS_PER_JOB,
            "but the cron pass outranks both -- the minimum count is owed by "
            "the job's slice, not by the pass",
        )

    def test_direct_trigger_honours_record_rules(self):
        self.env["ir.rule"].create(
            {
                "name": "no cron may be written",
                "model_id": self.env["ir.model"]._get_id("ir.cron"),
                "domain_force": "[(0, '=', 1)]",
                "perm_read": False,
                "perm_write": True,
                "perm_create": False,
                "perm_unlink": False,
            }
        )
        cron = self.cron.with_user(self.env.ref("base.user_admin"))
        with self.assertRaises(AccessError):
            cron.method_direct_trigger()


class TestIrCronDeactivationNotice(TransactionCase, CronMixinCase):
    def test_the_notice_names_the_failures_that_happened(self):
        cron = self.env["ir.cron"].create(self._get_cron_data(self.env))
        messages = []
        job = make_job(
            cron,
            failure_count=MIN_FAILURE_COUNT_BEFORE_DEACTIVATION + 6,
            first_failure_date=self.env.cr.now()
            - MIN_DELTA_BEFORE_DEACTIVATION
            - timedelta(days=1),
        )
        with patch.object(
            type(self.env["ir.cron"]),
            "_notify_admin",
            lambda self, message: messages.append(message),
        ):
            self.env["ir.cron"]._prepare_failure_vals(job, CompletionStatus.FAILED)

        self.assertEqual(len(messages), 1)
        self.assertIn(
            str(job.failure_count + 1),
            messages[0],
            "the notice must report the failures the job actually accumulated, "
            "not the threshold that made deactivation possible",
        )


class TestIrCronAttemptConvergence(TransactionCase, CronMixinCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.cron = cls.env["ir.cron"].create(cls._get_cron_data(cls.env))

    def _resolve(
        self,
        watermark,
        *,
        success,
        done,
        remaining,
        deactivate=False,
        loop_count=1,
        job=None,
    ):
        return IrCron._resolve_attempt(
            job if job is not None else make_job(self.cron),
            success=success,
            done=done,
            remaining=remaining,
            deactivate=deactivate,
            loop_count=loop_count,
            progress_watermark=watermark,
        )

    def _replay(self, attempts):
        watermark = ir_cron._Watermark()
        seen = []
        for success, done, remaining in attempts:
            status = self._resolve(
                watermark, success=success, done=done, remaining=remaining
            )
            seen.append(status)
            if status is not None:
                break
        return seen

    def test_a_strictly_converging_failure_runs_until_the_queue_empties(self):
        seen = self._replay([(False, 1, r) for r in (4, 3, 2, 1, 0)])
        self.assertEqual(
            seen,
            [None, None, None, None, CompletionStatus.FAILED],
            "this is the shape test_cron_process_job's failure_partial pins: "
            "raising on one record but moving past it every time",
        )

    def test_one_plateau_is_not_a_stall(self):
        seen = self._replay([(False, 1, r) for r in (5, 5, 4, 3, 2, 1, 0)])
        self.assertEqual(len(seen), 7)
        self.assertEqual(seen[-1], CompletionStatus.FAILED)
        self.assertTrue(
            all(status is None for status in seen[:-1]),
            "a reported queue length that pauses once and then resumes falling "
            "is still converging",
        )

    def test_a_queue_that_never_falls_ends_the_run(self):
        seen = self._replay([(False, 1, 5)] * 20)
        self.assertEqual(
            len(seen),
            MAX_STALLED_ATTEMPTS_PER_RUN + 1,
            "the first attempt sets the watermark; the next "
            f"{MAX_STALLED_ATTEMPTS_PER_RUN} fail to beat it",
        )
        self.assertEqual(seen[-1], CompletionStatus.FAILED)

    def test_a_success_between_failures_clears_the_stall(self):
        seen = self._replay(
            [(False, 1, 5), (False, 1, 5), (True, 1, 5), (False, 1, 5)] * 3
        )
        self.assertTrue(
            all(status is None for status in seen),
            "a good pass between failures means the job is not wedged; only a "
            "run of failures with no queue movement is",
        )

    def test_a_terminal_status_is_never_overridden_by_the_watermark(self):
        for success, done, remaining, expected in (
            (False, 0, 0, CompletionStatus.FAILED),
            (False, 0, 5, CompletionStatus.FAILED),
            (False, 3, 0, CompletionStatus.FAILED),
            (True, 3, 0, CompletionStatus.FULLY_DONE),
            (True, 0, 5, CompletionStatus.PARTIALLY_DONE),
        ):
            with self.subTest(success=success, done=done, remaining=remaining):
                watermark = ir_cron._Watermark()
                watermark.stalled = MAX_STALLED_ATTEMPTS_PER_RUN
                watermark.lowest_remaining = 0
                self.assertEqual(
                    self._resolve(
                        watermark, success=success, done=done, remaining=remaining
                    ),
                    expected,
                )

    def test_a_self_deactivating_job_marks_the_job_row(self):
        job = make_job(self.cron)
        status = self._resolve(
            ir_cron._Watermark(),
            success=True,
            done=1,
            remaining=0,
            deactivate=True,
            loop_count=0,
            job=job,
        )
        self.assertEqual(status, CompletionStatus.FULLY_DONE)
        self.assertTrue(
            job.deactivate,
            "_commit_progress(deactivate=True) has to reach _prepare_failure_vals, "
            "and the job object is the only channel between them",
        )


class TestCronJobRowContract(BaseCase):
    def test_every_field_the_run_reads_is_a_column_the_query_names(self):
        outcome = {"deactivate", "run_exception"}
        declared = {f.name for f in dataclasses.fields(CronJob)} - outcome
        selected = set(CronJob.COLUMNS) | set(CronJob.PROGRESS_COLUMNS)
        self.assertEqual(
            declared,
            selected,
            "_acquire_job names its columns instead of SELECT *, because that "
            "query joins ir_cron to a progress row and dictfetchone keeps only "
            "the LAST of two same-named columns -- so a new ir_cron column "
            "called done, remaining or timed_out_counter would silently "
            "shadow the progress value with no error anywhere",
        )

    def test_the_progress_columns_are_the_ones_the_join_supplies(self):
        self.assertEqual(
            set(CronJob.PROGRESS_COLUMNS),
            {"progress_id", "timed_out_counter"},
            "done and remaining were dropped when the timeout guard stopped "
            "reading them; nothing else in the run reads the acquired row's "
            "progress totals",
        )
