from datetime import timedelta

from odoo.exceptions import ValidationError

from .test_run_completion import RunCompletionCase
from .test_workflow_dag import link


class TimedEdgeCase(RunCompletionCase):
    def _age(self, runtime, action, **delta):
        line = self._line(runtime, action)
        line.date_settled -= timedelta(**delta)
        return line

    def _dispatch(self):
        self.env["automation.runtime"]._resume_waiting_executions()


class TestDelayedEdges(TimedEdgeCase):
    def test_a_delayed_edge_schedules_its_target(self):
        first = self._action("first")
        later = self._action("later")
        link(self.env, first, later, delay=2, delay_unit="hour")

        runtime = self._run()

        line = self._line(runtime, later)
        settled = self._line(runtime, first).date_settled
        self.assertEqual(line.state, "scheduled")
        self.assertEqual(line.date_resume, settled + timedelta(hours=2))
        self.assertEqual(runtime.state, "waiting_resume")

    def test_a_scheduled_step_asks_the_cron_to_run_when_it_is_due(self):
        cron = self.env.ref("automation.ir_cron_data_automation_resume")
        first = self._action("first")
        later = self._action("later")
        link(self.env, first, later, delay=1, delay_unit="day")

        runtime = self._run()

        due = self._line(runtime, later).date_resume
        triggers = self.env["ir.cron.trigger"].search([("cron_id", "=", cron.id)])
        self.assertIn(due, triggers.mapped("call_at"))

    def test_steps_due_at_the_same_time_share_one_cron_trigger(self):
        cron = self.env.ref("automation.ir_cron_data_automation_resume")
        first = self._action("first")
        later = self._action("later")
        other = self._action("other")
        link(self.env, first, later, delay=1, delay_unit="day")
        link(self.env, first, other, delay=1, delay_unit="day")
        before = self.env["ir.cron.trigger"].search_count([("cron_id", "=", cron.id)])

        self._run()

        self.assertEqual(
            self.env["ir.cron.trigger"].search_count([("cron_id", "=", cron.id)]),
            before + 1,
        )

    def test_a_scheduled_step_runs_once_due(self):
        first = self._action("first")
        later = self._action("later", "record.write({'ref': 'later ran'})")
        link(self.env, first, later, delay=2, delay_unit="hour")
        runtime = self._run()

        self._line(runtime, later).date_resume = self.env.cr.now()
        self._age(runtime, first, hours=3)
        self._dispatch()

        self.assertEqual(self._line(runtime, later).state, "done")
        self.assertEqual(runtime.state, "done")
        self.partner.invalidate_recordset(["ref"])
        self.assertEqual(self.partner.ref, "later ran")

    def test_the_cron_leaves_a_step_that_is_not_due(self):
        first = self._action("first")
        later = self._action("later")
        link(self.env, first, later, delay=2, delay_unit="hour")
        runtime = self._run()

        self._dispatch()

        self.assertEqual(self._line(runtime, later).state, "scheduled")

    def test_a_delay_of_zero_is_immediate(self):
        first = self._action("first")
        after = self._action("after")
        link(self.env, first, after, delay=0)

        runtime = self._run()

        self.assertEqual(self._line(runtime, after).state, "done")

    def test_a_negative_delay_is_refused(self):
        first, second = self._action("first"), self._action("second")

        with self.assertRaises(ValidationError):
            link(self.env, first, second, delay=-1)


class TestEventEdges(TimedEdgeCase):
    def test_an_event_edge_waits_for_its_event(self):
        send = self._action("send")
        opened = self._action("opened", "record.write({'ref': 'opened'})")
        link(self.env, send, opened, condition="event", event_code="open")

        runtime = self._run()

        self.assertEqual(self._line(runtime, opened).state, "waiting")
        self.assertEqual(
            runtime.state,
            "waiting_resume",
            "a run waiting on an event is waiting, not blocked",
        )

        self._line(runtime, send)._receive_event("open")

        self.assertEqual(self._line(runtime, opened).state, "done")
        self.assertEqual(runtime.state, "done")
        self.partner.invalidate_recordset(["ref"])
        self.assertEqual(self.partner.ref, "opened")

    def test_another_event_releases_nothing(self):
        send = self._action("send")
        opened = self._action("opened")
        link(self.env, send, opened, condition="event", event_code="open")
        runtime = self._run()

        self._line(runtime, send)._receive_event("click")

        self.assertEqual(self._line(runtime, opened).state, "waiting")

    def test_an_event_edge_can_delay_after_the_event(self):
        send = self._action("send")
        followup = self._action("followup")
        link(
            self.env,
            send,
            followup,
            condition="event",
            event_code="open",
            delay=1,
            delay_unit="hour",
        )
        runtime = self._run()

        self._line(runtime, send)._receive_event("open")

        line = self._line(runtime, followup)
        self.assertEqual(line.state, "scheduled")
        self.assertEqual(
            line.date_resume,
            line.edge_in_ids.date_event + timedelta(hours=1),
        )

    def test_an_event_before_the_window_closes_skips_the_no_event_branch(self):
        send = self._action("send")
        reminder = self._action("reminder")
        link(
            self.env,
            send,
            reminder,
            condition="no_event",
            event_code="open",
            delay=2,
            delay_unit="day",
        )
        runtime = self._run()
        self.assertEqual(self._line(runtime, reminder).state, "scheduled")

        self._line(runtime, send)._receive_event("open")

        self.assertEqual(self._line(runtime, reminder).state, "skipped")
        self.assertEqual(runtime.state, "done")

    def test_a_no_event_branch_runs_when_the_window_closes(self):
        send = self._action("send")
        opened = self._action("opened")
        reminder = self._action("reminder")
        link(self.env, send, opened, condition="event", event_code="open")
        link(
            self.env,
            send,
            reminder,
            condition="no_event",
            event_code="open",
            delay=2,
            delay_unit="day",
        )
        runtime = self._run()

        self._age(runtime, send, days=3)
        self._line(runtime, reminder).date_resume = self.env.cr.now()
        self._dispatch()

        self.assertEqual(self._line(runtime, reminder).state, "done")
        self.assertEqual(self._line(runtime, opened).state, "waiting")
        self.assertEqual(runtime.state, "waiting_resume")

        self._line(runtime, send)._receive_event("open")

        self.assertEqual(self._line(runtime, opened).state, "done")
        self.assertEqual(runtime.state, "done")

    def test_an_exclusive_event_revokes_the_other_branches(self):
        send = self._action("send")
        followup = self._action("followup")
        bounced = self._action("bounced")
        link(self.env, send, followup, delay=1, delay_unit="day")
        link(self.env, send, bounced, condition="event", event_code="bounce")
        runtime = self._run()
        self.assertEqual(self._line(runtime, followup).state, "scheduled")

        self._line(runtime, send)._receive_event("bounce", exclusive=True)

        self.assertEqual(self._line(runtime, followup).state, "skipped")
        self.assertEqual(self._line(runtime, bounced).state, "done")
        self.assertEqual(runtime.state, "done")

    def test_an_event_edge_needs_an_event_code(self):
        first, second = self._action("first"), self._action("second")

        with self.assertRaises(ValidationError):
            link(self.env, first, second, condition="event")

    def test_a_no_event_edge_refuses_a_negative_window(self):
        first, second = self._action("first"), self._action("second")

        with self.assertRaises(ValidationError):
            link(
                self.env,
                first,
                second,
                condition="no_event",
                event_code="open",
                delay=-1,
            )


class TestEdgeTimingTravels(TimedEdgeCase):
    def test_copying_an_automation_carries_edge_timing(self):
        send, remind = self._action("send"), self._action("remind")
        link(
            self.env,
            send,
            remind,
            condition="no_event",
            event_code="open",
            delay=3,
            delay_unit="week",
        )

        copied = self.automation.copy().edge_ids

        self.assertEqual(
            (copied.condition, copied.event_code, copied.delay, copied.delay_unit),
            ("no_event", "open", 3, "week"),
        )

    def test_the_graph_payload_carries_edge_timing(self):
        send, opened = self._action("send"), self._action("opened")
        link(
            self.env,
            send,
            opened,
            condition="event",
            event_code="open",
            delay=2,
            delay_unit="day",
        )

        graph = self.automation.get_workflow_graph()
        (edge,) = graph["edges"]

        self.assertEqual(
            (edge["event_code"], edge["delay"], edge["delay_unit"]),
            ("open", 2, "day"),
        )
        self.assertEqual(
            edge["event_label"], "", "only an application knows how to name its events"
        )
        self.assertEqual({node["detail"] for node in graph["nodes"]}, {""})
