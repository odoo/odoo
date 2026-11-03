from datetime import datetime
from unittest.mock import patch

from freezegun import freeze_time

from odoo.addons.bus.tests.common import BusResult
from odoo.addons.mail.tests.common import MailCommon
from odoo.addons.mail.tools.discuss import Store
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestImStatusChanges(MailCommon):
    def _run_cron(self, lastcall=None):
        users = self.env["res.users"]
        if lastcall:
            users = users.with_context(lastcall=lastcall)
        with self.mock_datetime_and_now("2026-10-27 14:00:00"):
            users._cron_send_im_status_changes()

    def test_window_and_target(self):
        windows = []
        user = self.user_employee

        def add_im_status_changes(self, stores, since, until):
            windows.append((since, until))
            stores[user, "presence_internal"].add(user, {"is_in_meeting": True})

        with (
            patch.object(
                self.registry["res.users"],
                "_add_im_status_changes",
                add_im_status_changes,
            ),
            self.assertBus(
                BusResult(
                    (user, "presence_internal"),
                    "mail.record/insert",
                    Store().add(user, {"is_in_meeting": True}),
                )
            ),
        ):
            self._run_cron(lastcall=datetime(2026, 10, 27, 13, 55))
        self.assertEqual(
            windows, [(datetime(2026, 10, 27, 13, 55), datetime(2026, 10, 27, 14))]
        )

    def test_first_run_without_lastcall(self):
        windows = []

        def add_im_status_changes(self, stores, since, until):
            windows.append((since, until))

        with patch.object(
            self.registry["res.users"], "_add_im_status_changes", add_im_status_changes
        ):
            self._run_cron()
        self.assertEqual(
            windows, [(datetime(2026, 10, 27, 13, 59), datetime(2026, 10, 27, 14))]
        )

    def test_no_change_no_notification(self):
        with self.assertBus([]):
            self._run_cron()

    def _cron_trigger_times(self):
        cron = self.env.ref("mail.ir_cron_send_im_status_changes")
        return (
            self.env["ir.cron.trigger"]
            .sudo()
            .search([("cron_id", "=", cron.id)])
            .mapped("call_at")
        )

    def test_triggers_itself_after_next_change(self):
        afters = []

        def get_next_im_status_change(self, after):
            afters.append(after)
            return datetime(2026, 10, 27, 15)

        with patch.object(
            self.registry["res.users"],
            "_get_next_im_status_change",
            get_next_im_status_change,
        ):
            self._run_cron()
        self.assertEqual(afters, [datetime(2026, 10, 27, 14)])
        self.assertIn(datetime(2026, 10, 27, 15, 0, 1), self._cron_trigger_times())

    def test_next_change_during_the_run_is_triggered(self):
        def get_next_im_status_change(self, after):
            return datetime(2026, 10, 27, 14, 0, 10)

        # the run started at 14:00 (transaction time) and ends at 14:00:30
        with (
            patch.object(
                self.registry["res.users"],
                "_get_next_im_status_change",
                get_next_im_status_change,
            ),
            freeze_time("2026-10-27 14:00:30"),
            patch.object(self.env.cr, "now", lambda: datetime(2026, 10, 27, 14)),
        ):
            self.env["res.users"]._cron_send_im_status_changes()
        self.assertEqual(self._cron_trigger_times(), [datetime(2026, 10, 27, 14, 0, 11)])

    def test_trigger_at_without_cron(self):
        self.env.ref("mail.ir_cron_send_im_status_changes").unlink()
        self.env["res.users"]._trigger_im_status_changes_at([datetime(2100, 1, 1)])

    def test_trigger_at_skips_past(self):
        with self.mock_datetime_and_now("2026-10-27 14:00:00"):
            self.env["res.users"]._trigger_im_status_changes_at(
                [datetime(2026, 10, 27, 13), datetime(2026, 10, 27, 16)]
            )
        self.assertEqual(self._cron_trigger_times(), [datetime(2026, 10, 27, 16, 0, 1)])
