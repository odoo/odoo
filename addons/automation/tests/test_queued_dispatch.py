from datetime import timedelta
from unittest.mock import patch

from odoo.tools import mute_logger

from .test_run_completion import RunCompletionCase
from .test_workflow_dag import link


class QueuedCase(RunCompletionCase):
    def setUp(self):
        super().setUp()
        self.automation.run_mode = "queued"
        self.partners = self.partner | self.env["res.partner"].create(
            [{"name": "Queued Partner 2"}, {"name": "Queued Partner 3"}]
        )
        self.cron = self.env.ref("automation.ir_cron_data_automation_resume")

    def _launch(self, partners=None):
        return self.automation._run_through_runtimes(partners or self.partners)

    def _dispatch(self):
        return self.env["automation.runtime"]._dispatch_due_steps()

    def _cron_trigger_count(self):
        return self.env["ir.cron.trigger"].search_count(
            [("cron_id", "=", self.cron.id)]
        )


class TestQueuedRuns(QueuedCase):
    def test_a_queued_run_executes_nothing_when_it_starts(self):
        first = self._action("first", "record.write({'ref': 'ran'})")
        before = self._cron_trigger_count()

        runtimes = self._launch()

        self.assertEqual(set(runtimes.mapped("state")), {"in_progress"})
        self.assertEqual(
            set(
                runtimes.line_ids.filtered(lambda l: l.action_id == first).mapped(
                    "state"
                )
            ),
            {"ready"},
        )
        self.assertGreater(self._cron_trigger_count(), before)
        self.assertFalse(any(self.partners.mapped("ref")))

    def test_launching_many_runs_asks_the_cron_once(self):
        self._action("first")
        before = self._cron_trigger_count()

        self._launch()

        self.assertEqual(self._cron_trigger_count(), before + 1)

    def test_the_dispatcher_runs_queued_steps_to_the_end(self):
        first = self._action("first", "record.write({'ref': 'first'})")
        second = self._action("second", "record.write({'function': 'second'})")
        link(self.env, first, second)
        runtimes = self._launch()

        self._dispatch()

        self.assertEqual(set(runtimes.mapped("state")), {"done"})
        self.partners.invalidate_recordset(["ref", "function"])
        self.assertEqual(set(self.partners.mapped("ref")), {"first"})
        self.assertEqual(set(self.partners.mapped("function")), {"second"})

    def test_the_dispatcher_hands_each_node_its_whole_batch(self):
        first = self._action("first")
        second = self._action("second")
        link(self.env, first, second)
        runtimes = self._launch()
        Action = type(self.env["ir.actions.server"])
        batches = []
        original = Action._execute_runtime_lines

        def spy(action, lines):
            batches.append((action.name, len(lines)))
            return original(action, lines)

        with patch.object(Action, "_execute_runtime_lines", spy):
            self._dispatch()

        self.assertEqual(batches, [("first", 3), ("second", 3)])
        self.assertEqual(set(runtimes.mapped("state")), {"done"})

    @mute_logger("odoo.addons.automation.models.automation_runtime_line")
    def test_one_failing_step_does_not_stop_its_batch(self):
        self._action(
            "first",
            "if record.name == 'Queued Partner 2':\n"
            "    raise ValueError('boom')\n"
            "record.write({'ref': 'reached'})",
        )
        runtimes = self._launch()

        self._dispatch()

        failed = runtimes.filtered(lambda run: run.res_id == self.partners[1].id)
        self.assertEqual(failed.state, "error")
        self.assertEqual(set((runtimes - failed).mapped("state")), {"done"})

    def test_the_dispatcher_leaves_immediate_runs_alone(self):
        self.automation.run_mode = "immediate"
        first = self._action("first", "record.write({'ref': 'manual'})")
        runtime = self.env["automation.runtime"].create(
            {
                "automation_id": self.automation.id,
                "res_model": "res.partner",
                "res_id": self.partner.id,
            }
        )
        runtime.action_start()

        self._dispatch()

        self.assertEqual(self._line(runtime, first).state, "ready")

    def test_the_dispatcher_commits_nothing_outside_a_cron(self):
        self._action("first")
        self._launch()

        with patch.object(
            type(self.env["ir.cron"]), "_commit_progress", side_effect=AssertionError
        ):
            self._dispatch()

    def test_the_dispatcher_hands_over_to_the_next_cron_call_when_time_is_up(self):
        first = self._action("first")
        second = self._action("second")
        link(self.env, first, second)
        runtimes = self._launch()
        before = self._cron_trigger_count()

        with patch.object(
            type(self.env["ir.cron"]), "_commit_progress", return_value=0
        ) as commit:
            self.env["automation.runtime"].with_context(
                cron_id=self.cron.id
            )._dispatch_due_steps()

        commit.assert_called_once_with(3)
        self.assertEqual(
            set(
                runtimes.line_ids.filtered(lambda l: l.action_id == second).mapped(
                    "state"
                )
            ),
            {"ready"},
        )
        self.assertGreater(self._cron_trigger_count(), before)

    def test_a_delayed_step_of_a_queued_run_runs_once_due(self):
        first = self._action("first")
        later = self._action("later", "record.write({'ref': 'later'})")
        link(self.env, first, later, delay=1, delay_unit="hour")
        (runtime,) = self._launch(self.partner)
        self._dispatch()
        self.assertEqual(self._line(runtime, later).state, "scheduled")
        self.assertEqual(runtime.state, "waiting_resume")

        line = self._line(runtime, first)
        line.date_settled -= timedelta(hours=2)
        self._line(runtime, later).date_resume = self.env.cr.now()
        self._dispatch()

        self.assertEqual(self._line(runtime, later).state, "done")
        self.assertEqual(runtime.state, "done")

    def test_an_event_on_a_queued_run_is_executed_by_the_dispatcher(self):
        send = self._action("send")
        opened = self._action("opened", "record.write({'ref': 'opened'})")
        link(self.env, send, opened, condition="event", event_code="open")
        (runtime,) = self._launch(self.partner)
        self._dispatch()
        self.assertEqual(runtime.state, "waiting_resume")

        self._line(runtime, send)._receive_event("open")

        self.assertEqual(self._line(runtime, opened).state, "ready")
        self._dispatch()
        self.assertEqual(self._line(runtime, opened).state, "done")
        self.assertEqual(runtime.state, "done")
