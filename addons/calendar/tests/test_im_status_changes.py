from datetime import datetime

from odoo import Command
from odoo.addons.bus.tests.common import BusResult
from odoo.addons.mail.tests.common import MailCommon
from odoo.addons.mail.tools.discuss import Store
from odoo.tests import tagged


def dt(hour, minute=0):
    return datetime(2026, 10, 27, hour, minute)


@tagged("post_install", "-at_install")
class TestImStatusChanges(MailCommon):
    def _create_event(self, start, stop, users=None, state="accepted", **vals):
        users = users or self.user_employee
        event = self.env["calendar.event"].create(
            {
                "name": "meeting",
                "start": start,
                "stop": stop,
                "show_as": "busy",
                "partner_ids": [Command.set(users.partner_id.ids)],
                **vals,
            }
        )
        event.attendee_ids.filtered(
            lambda a: a.partner_id in users.partner_id
        ).state = state
        return event

    def _run_cron(self, since, until):
        with self.mock_datetime_and_now(until):
            self.env["res.users"].with_context(
                lastcall=since
            )._cron_send_im_status_changes()

    def _expected(self, users, value):
        return BusResult(
            (users, "presence_internal"),
            "mail.record/insert",
            Store().add(users, {"is_in_meeting": value}),
        )

    def test_meeting_start_sends_true(self):
        self._create_event(dt(14), dt(15))
        with self.assertBus(self._expected(self.user_employee, True)):
            self._run_cron(dt(13, 59), dt(14, 1))

    def test_meeting_end_sends_false(self):
        self._create_event(dt(14), dt(15))
        with self.assertBus(self._expected(self.user_employee, False)):
            self._run_cron(dt(14, 59), dt(15, 1))

    def test_back_to_back_sends_nothing(self):
        self._create_event(dt(13), dt(14))
        self._create_event(dt(14), dt(15))
        with self.assertBus([]):
            self._run_cron(dt(13, 59), dt(14, 1))

    def test_stop_on_window_edge(self):
        self._create_event(dt(14), dt(15))
        with self.assertBus([]):
            self._run_cron(dt(14, 59), dt(15))
        with self.assertBus(self._expected(self.user_employee, False)):
            self._run_cron(dt(15), dt(15, 1))

    def test_late_cron_net_change_only(self):
        self._create_event(dt(13), dt(14))
        with self.assertBus([]):
            self._run_cron(dt(12), dt(15))

    def test_declined_draft_free_ignored(self):
        self._create_event(dt(14), dt(15), state="declined")
        self._create_event(dt(14), dt(15), is_draft=True)
        self._create_event(dt(14), dt(15), show_as="free")
        with self.assertBus([]):
            self._run_cron(dt(13, 59), dt(14, 1))

    def _next_change(self, after):
        return self.env["res.users"]._get_next_im_status_change(after)

    def _cron_trigger_times(self):
        cron = self.env.ref("mail.ir_cron_send_im_status_changes")
        return sorted(
            self.env["ir.cron.trigger"]
            .sudo()
            .search([("cron_id", "=", cron.id)])
            .mapped("call_at")
        )

    def test_next_change_is_next_boundary(self):
        self._create_event(dt(14), dt(15))
        self._create_event(dt(16), dt(17), show_as="free")
        self._create_event(dt(18), dt(19))
        self.assertEqual(self._next_change(dt(13)), dt(14))
        self.assertEqual(self._next_change(dt(14, 30)), dt(15))
        self.assertEqual(self._next_change(dt(15)), dt(15))
        self.assertEqual(self._next_change(dt(15, 30)), dt(18))

    def test_event_write_triggers_its_boundaries(self):
        with self.mock_datetime_and_now(dt(13)):
            event = self._create_event(dt(14), dt(15))
            self.env["ir.cron.trigger"].sudo().search([]).unlink()
            event.write({"start": dt(14, 30), "stop": dt(15, 30)})
        self.assertEqual(
            self._cron_trigger_times(),
            [dt(14, 30).replace(second=1), dt(15, 30).replace(second=1)],
        )

    def test_attendee_accept_triggers_boundaries(self):
        with self.mock_datetime_and_now(dt(13)):
            event = self._create_event(dt(14), dt(15), state="needsAction")
            self.env["ir.cron.trigger"].sudo().search([]).unlink()
            event.attendee_ids.state = "accepted"
        self.assertEqual(
            self._cron_trigger_times(),
            [dt(14).replace(second=1), dt(15).replace(second=1)],
        )

    def test_create_ongoing_event_sends_true(self):
        with (
            self.mock_datetime_and_now(dt(14, 30)),
            self.assertBus(
                [
                    BusResult(self.user_employee, "calendar.alarm", []),
                    self._expected(self.user_employee, True),
                ]
            ),
        ):
            self._create_event(dt(14), dt(15))

    def test_edits_ending_ongoing_meeting_send_false(self):
        ended = self._expected(self.user_employee, False)
        alarm = BusResult(self.user_employee, "calendar.alarm", [])
        for edit, notifications in (
            (lambda event: event.unlink(), [ended, alarm]),
            (lambda event: event.write({"active": False}), [ended]),
            (lambda event: event.write({"stop": dt(14, 15)}), [ended]),
            (lambda event: event.attendee_ids.write({"state": "declined"}), [ended]),
            (lambda event: event.attendee_ids.unlink(), [ended]),
        ):
            with self.subTest(edit=edit), self.mock_datetime_and_now(dt(14, 30)):
                event = self._create_event(dt(14), dt(15))
                with self.assertBus(notifications):
                    edit(event)
