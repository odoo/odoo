from datetime import timedelta

from odoo.tools import mute_logger

from .test_queued_dispatch import QueuedCase
from .test_run_completion import RunCompletionCase
from .test_workflow_dag import link


class TestSkipReasons(RunCompletionCase):
    def test_a_branch_not_taken_says_so(self):
        first = self._action("first")
        untaken = self._action("untaken")
        link(self.env, first, untaken, condition="expression", condition_expr="False")

        runtime = self._run()

        self.assertEqual(self._line(runtime, untaken).skip_reason, "branch")

    def test_a_revoked_branch_says_so(self):
        send = self._action("send")
        followup = self._action("followup")
        bounced = self._action("bounced")
        link(self.env, send, followup, delay=1, delay_unit="day")
        link(self.env, send, bounced, condition="event", event_code="bounce")
        runtime = self._run()

        self._line(runtime, send)._receive_event("bounce", exclusive=True)

        self.assertEqual(self._line(runtime, followup).skip_reason, "revoked")

    def test_a_caller_can_skip_a_step_with_its_own_reason(self):
        pause = self._action("pause", node_type="wait", wait_delay=1)
        after = self._action("after")
        link(self.env, pause, after)
        runtime = self._run()
        line = self._line(runtime, after)

        line._skip(reason="filtered", message="not in the audience")

        self.assertEqual(line.state, "skipped")
        self.assertEqual(line.skip_reason, "filtered")
        self.assertEqual(line.error_message, "not in the audience")


class TestStartDelay(QueuedCase):
    def test_a_root_step_with_a_start_delay_is_scheduled(self):
        first = self._action("first", start_delay=2, start_delay_unit="hour")

        (runtime,) = self._launch(self.partner)

        line = self._line(runtime, first)
        self.assertEqual(line.state, "scheduled")
        self.assertEqual(line.date_resume, line.create_date + timedelta(hours=2))

    def test_a_delayed_root_step_runs_once_due(self):
        first = self._action(
            "first",
            "record.write({'ref': 'started'})",
            start_delay=2,
            start_delay_unit="hour",
        )
        (runtime,) = self._launch(self.partner)
        self._dispatch()
        self.assertEqual(runtime.state, "waiting_resume")

        line = self._line(runtime, first)
        line.flush_recordset()
        self.env.cr.execute(
            "UPDATE automation_runtime_line SET create_date = create_date - interval "
            "'3 hours', date_resume = now() at time zone 'UTC' WHERE id = %s",
            [line.id],
        )
        line.invalidate_recordset(["create_date", "date_resume"])
        self._dispatch()

        self.assertEqual(line.state, "done")
        self.assertEqual(runtime.state, "done")

    def test_a_start_delay_on_a_step_with_predecessors_is_ignored(self):
        first = self._action("first")
        second = self._action("second", start_delay=5, start_delay_unit="day")
        link(self.env, first, second)
        (runtime,) = self._launch(self.partner)

        self._dispatch()

        self.assertEqual(self._line(runtime, second).state, "done")


class TestSyncToDefinition(QueuedCase):
    def test_a_step_added_after_the_run_started_joins_it(self):
        first = self._action("first")
        pause = self._action("pause", node_type="wait", wait_delay=1)
        link(self.env, first, pause)
        (runtime,) = self._launch(self.partner)
        self._dispatch()

        added = self._action("added", "record.write({'ref': 'added'})")
        link(self.env, first, added)
        runtime._sync_to_definition()
        self._dispatch()

        self.assertEqual(self._line(runtime, added).state, "done")
        self.partner.invalidate_recordset(["ref"])
        self.assertEqual(self.partner.ref, "added")

    def test_a_changed_delay_reschedules_a_step_not_yet_reached(self):
        first = self._action("first")
        later = self._action("later")
        edge = link(self.env, first, later, delay=1, delay_unit="day")
        (runtime,) = self._launch(self.partner)
        self._dispatch()
        settled = self._line(runtime, first).date_settled

        edge.write({"delay": 3})
        runtime._sync_to_definition()

        self.assertEqual(
            self._line(runtime, later).date_resume, settled + timedelta(days=3)
        )

    def test_a_ready_step_not_yet_run_takes_a_changed_delay(self):
        first = self._action("first")
        later = self._action("later")
        edge = link(self.env, first, later)
        (runtime,) = self._launch(self.partner)
        self.automation.active = False
        self._line(runtime, first).action_execute()
        self.assertEqual(self._line(runtime, later).state, "ready")
        settled = self._line(runtime, first).date_settled

        edge.write({"delay": 2, "delay_unit": "day"})
        runtime._sync_to_definition()

        self.assertEqual(self._line(runtime, later).state, "scheduled")
        self.assertEqual(
            self._line(runtime, later).date_resume, settled + timedelta(days=2)
        )

    def test_a_changed_start_delay_reschedules_a_root_not_yet_started(self):
        first = self._action("first", start_delay=1, start_delay_unit="day")
        (runtime,) = self._launch(self.partner)
        line = self._line(runtime, first)

        first.start_delay = 3
        runtime._sync_to_definition()

        self.assertEqual(line.date_resume, line.create_date + timedelta(days=3))

    def test_a_step_already_run_keeps_the_conditions_it_ran_under(self):
        first = self._action("first")
        second = self._action("second")
        edge = link(self.env, first, second)
        (runtime,) = self._launch(self.partner)
        self._dispatch()

        edge.write({"delay": 3, "delay_unit": "day"})
        runtime._sync_to_definition()

        runtime_edge = self._line(runtime, second).edge_in_ids
        self.assertEqual(runtime_edge.delay, 0)
        self.assertEqual(self._line(runtime, second).state, "done")

    def test_a_finished_run_is_left_alone(self):
        self._action("first")
        (runtime,) = self._launch(self.partner)
        self._dispatch()
        self.assertEqual(runtime.state, "done")

        self._action("added")
        runtime._sync_to_definition()

        self.assertEqual(len(runtime.line_ids), 1)


class TestAddSteps(QueuedCase):
    def test_a_step_can_be_added_to_running_runs_alone(self):
        first = self._action("first")
        pause = self._action("pause", node_type="wait", wait_delay=1)
        link(self.env, first, pause)
        runtimes = self._launch()
        self._dispatch()
        new_root = self._action("new root")
        child = self._action("child", "record.write({'ref': 'child'})")
        link(self.env, first, child)

        runtimes._add_steps(child)
        self._dispatch()

        for runtime in runtimes:
            self.assertEqual(self._line(runtime, child).state, "done")
            self.assertFalse(self._line(runtime, new_root))

    def test_a_ready_step_keeps_the_date_it_became_due(self):
        first = self._action("first")
        later = self._action("later")
        link(self.env, first, later, delay=1, delay_unit="hour")
        (runtime,) = self._launch(self.partner)
        self.automation.active = False
        first_line = self._line(runtime, first)
        first_line.action_execute()
        first_line.date_settled -= timedelta(hours=3)

        self._line(runtime, later)._settle_readiness()

        later_line = self._line(runtime, later)
        self.assertEqual(later_line.state, "ready")
        self.assertEqual(
            later_line.date_resume, first_line.date_settled + timedelta(hours=1)
        )


class TestArchivedRule(QueuedCase):
    def test_an_archived_rule_is_not_dispatched(self):
        first = self._action("first", "record.write({'ref': 'ran'})")
        (runtime,) = self._launch(self.partner)

        self.automation.active = False
        self._dispatch()

        self.assertEqual(self._line(runtime, first).state, "ready")

        self.automation.active = True
        self._dispatch()

        self.assertEqual(self._line(runtime, first).state, "done")

    def test_an_archived_rule_named_explicitly_is_dispatched(self):
        first = self._action("first")
        (runtime,) = self._launch(self.partner)
        self.automation.active = False

        self.env["automation.runtime"]._dispatch_due_steps(rules=self.automation)

        self.assertEqual(self._line(runtime, first).state, "done")


class TestStepErrorPolicy(QueuedCase):
    def test_by_default_a_failed_step_fails_its_run(self):
        failing = self._action("failing", "raise ValueError('boom')")
        after = self._action("after")
        other = self._action("other", node_type="wait", wait_delay=1)
        link(self.env, failing, after)
        (runtime,) = self._launch(self.partner)

        with mute_logger("odoo.addons.automation.models.automation_runtime_line"):
            self._dispatch()

        self.assertEqual(runtime.state, "error")
        self.assertEqual(self._line(runtime, other).state, "error")

    def test_a_rule_can_close_only_the_failed_branch(self):
        self.automation.step_error_policy = "close_branch"
        failing = self._action("failing", "raise ValueError('boom')")
        after = self._action("after")
        other = self._action("other", node_type="wait", wait_delay=1)
        link(self.env, failing, after)
        (runtime,) = self._launch(self.partner)

        with mute_logger("odoo.addons.automation.models.automation_runtime_line"):
            self._dispatch()

        self.assertEqual(self._line(runtime, failing).state, "error")
        self.assertEqual(self._line(runtime, after).state, "skipped")
        self.assertEqual(self._line(runtime, other).state, "paused")
        self.assertEqual(runtime.state, "waiting_resume")


class TestScopedDispatch(QueuedCase):
    def test_the_dispatcher_can_be_scoped_to_some_rules(self):
        mine = self._action("mine")
        other_rule = self.automation.copy({"name": "Other queued"})
        (runtime,) = self._launch(self.partner)
        (other_runtime,) = other_rule._run_through_runtimes(self.partner)

        self.env["automation.runtime"]._dispatch_due_steps(rules=other_rule)

        self.assertEqual(self._line(runtime, mine).state, "ready")
        self.assertEqual(other_runtime.state, "done")


class TestZeroWindow(RunCompletionCase):
    def test_a_no_event_edge_without_a_window_fires_when_its_source_settles(self):
        send = self._action("send")
        reminder = self._action("reminder")
        link(self.env, send, reminder, condition="no_event", event_code="open")

        runtime = self._run()

        self.assertEqual(self._line(runtime, reminder).state, "done")


class TestCancelledReason(RunCompletionCase):
    def test_a_step_can_be_called_off(self):
        pause = self._action("pause", node_type="wait", wait_delay=1)
        after = self._action("after")
        link(self.env, pause, after)
        runtime = self._run()

        self._line(runtime, after)._skip(reason="cancelled", message="Manually")

        self.assertEqual(self._line(runtime, after).skip_reason, "cancelled")
