import contextlib
import itertools
from types import SimpleNamespace
from unittest.mock import patch

from odoo.exceptions import AccessDenied
from odoo.tests.common import TransactionCase, new_test_user, tagged

from odoo.addons.base.models import ir_autovacuum

_IR_AUTOVACUUM_LOGGER = "odoo.addons.base.models.ir_autovacuum"


@tagged("post_install", "-at_install")
class TestAutovacuumDispatcher(TransactionCase):
    def test_run_vacuum_requires_cron_id_in_context(self):
        autovacuum = self.env["ir.autovacuum"]
        self.assertTrue(autovacuum.env.is_admin())
        self.assertFalse(autovacuum.env.context.get("cron_id"))
        with self.assertRaises(AccessDenied):
            autovacuum._run_vacuum_cleaner()

    def test_run_vacuum_requires_admin(self):
        user = new_test_user(self.env, login="av_plain_user")
        autovacuum = self.env["ir.autovacuum"].with_user(user).with_context(cron_id=1)
        self.assertFalse(autovacuum.env.is_admin())
        self.assertTrue(autovacuum.env.context.get("cron_id"))
        with self.assertRaises(AccessDenied):
            autovacuum._run_vacuum_cleaner()


@tagged("post_install", "-at_install")
class TestAutovacuumTimeBudget(TransactionCase):
    @staticmethod
    def _getmembers_stub(methods):

        def fake_getmembers(cls, predicate=None):
            if getattr(cls, "_name", None) == "ir.autovacuum":
                return methods
            return []

        return fake_getmembers

    def _run(self, methods, fake_time=None, progress_calls=None, **context):
        autovacuum = self.env["ir.autovacuum"].with_context(cron_id=1, **context)

        def fake_commit_progress(cron, *args, **kwargs):
            if progress_calls is not None:
                progress_calls.append((args, kwargs))
            return float("inf")

        with contextlib.ExitStack() as stack:
            stack.enter_context(
                patch.object(
                    ir_autovacuum,
                    "inspect",
                    SimpleNamespace(getmembers=self._getmembers_stub(methods)),
                )
            )
            stack.enter_context(
                patch.object(
                    type(self.env["ir.cron"]), "_commit_progress", fake_commit_progress
                )
            )
            if fake_time is not None:
                stack.enter_context(patch.object(ir_autovacuum, "time", fake_time))
            autovacuum._run_vacuum_cleaner()

    def test_within_budget_requeues_remaining_work(self):
        calls = []

        def fake_gc(model):
            calls.append(model._name)
            return (1, len(calls) == 1)

        with self.assertNoLogs(_IR_AUTOVACUUM_LOGGER, level="WARNING"):
            self._run([("_gc_fake", fake_gc)])
        self.assertEqual(calls, ["ir.autovacuum", "ir.autovacuum"])

    def test_budget_exceeded_stops_requeueing(self):
        calls = []

        def fake_gc(model):
            calls.append(model._name)
            return (1, 12345)

        ticks = itertools.count(start=0, step=2000)
        fake_time = SimpleNamespace(monotonic=lambda: next(ticks))
        with self.assertLogs(_IR_AUTOVACUUM_LOGGER, level="WARNING") as capture:
            self._run([("_gc_fake", fake_gc)], fake_time=fake_time)
        self.assertEqual(calls, ["ir.autovacuum"])
        warning = "\n".join(capture.output)
        self.assertIn("wall-clock budget", warning)
        self.assertIn("ir.autovacuum._gc_fake", warning)
        self.assertIn("12345", warning)

    def test_budget_does_not_skip_first_pass(self):
        calls = []

        def fake_gc_a(model):
            calls.append("a")
            return (1, True)

        def fake_gc_b(model):
            calls.append("b")
            return (1, False)

        ticks = itertools.count(start=0, step=2000)
        fake_time = SimpleNamespace(monotonic=lambda: next(ticks))
        with self.assertLogs(_IR_AUTOVACUUM_LOGGER, level="WARNING"):
            self._run(
                [("_gc_fake_a", fake_gc_a), ("_gc_fake_b", fake_gc_b)],
                fake_time=fake_time,
            )
        self.assertEqual(sorted(calls), ["a", "b"])
        self.assertEqual(len(calls), 2)

    def test_the_pass_deadline_stops_the_loop_and_reports_remaining_work(self):
        calls = []

        def fake_gc_a(model):
            calls.append("a")
            return (1, 7)

        def fake_gc_b(model):
            calls.append("b")
            return (1, False)

        ticks = itertools.count(start=0, step=3)
        fake_time = SimpleNamespace(monotonic=lambda: next(ticks))
        progress_calls = []
        with (
            patch.object(ir_autovacuum.random, "shuffle", lambda methods: None),
            self.assertLogs(_IR_AUTOVACUUM_LOGGER, level="WARNING") as capture,
        ):
            self._run(
                [("_gc_fake_a", fake_gc_a), ("_gc_fake_b", fake_gc_b)],
                fake_time=fake_time,
                progress_calls=progress_calls,
                cron_hard_deadline=5,
            )
        self.assertEqual(calls, ["b"], "one pass, then the deadline is hit")
        warning = "\n".join(capture.output)
        self.assertIn("wall-clock budget", warning)
        self.assertIn("_gc_fake_a (remaining: 'not started')", warning)
        self.assertIn(
            ((), {"remaining": 1}),
            progress_calls,
            "the cron must end PARTIALLY_DONE so the next pass resumes the sweep",
        )

    def test_a_malformed_return_is_reported_and_not_requeued(self):
        calls = []

        def fake_gc(model):
            calls.append(model._name)
            return "everything"

        with self.assertLogs(_IR_AUTOVACUUM_LOGGER, level="WARNING") as capture:
            self._run([("_gc_fake", fake_gc)])
        self.assertEqual(calls, ["ir.autovacuum"])
        self.assertIn("(done, remaining)", "\n".join(capture.output))
        self.assertIn("'everything'", "\n".join(capture.output))

    def test_transient_vacuum_reports_a_count_and_a_flag(self):
        done, more = self.env[
            "base.partner.merge.automatic.wizard"
        ]._vacuum_transient_rows()
        self.assertIsInstance(done, int)
        self.assertIs(more, False)


@tagged("post_install", "-at_install")
class TestTransientVacuumOverCount(TransactionCase):
    def test_the_backlog_probe_and_the_over_count_removal(self):
        Wizard = self.env["base.partner.merge.automatic.wizard"]
        rows = Wizard.create([{}, {}, {}])
        rows.flush_recordset()
        total = Wizard.search_count([])
        self.assertTrue(self.env.backend.has_rows_beyond(Wizard, total - 1))
        self.assertFalse(self.env.backend.has_rows_beyond(Wizard, total))

        # under the count: nothing is touched, however old the rows
        self.assertEqual(Wizard._remove_transient_rows_over_count(total), 0)
        self.assertEqual(rows.exists(), rows)

        # over the count: only the rows old enough go, the young one stays
        self.env.cr.execute(
            "UPDATE base_partner_merge_automatic_wizard"
            " SET write_date = write_date - interval '1 day' WHERE id = ANY(%s)",
            [rows[:2].ids],
        )
        rows.invalidate_recordset(["write_date"])
        removed = Wizard._remove_transient_rows_over_count(total - 1)
        self.assertGreaterEqual(removed, 2)
        self.assertFalse(rows[:2].exists())
        self.assertEqual(rows[2].exists(), rows[2])
