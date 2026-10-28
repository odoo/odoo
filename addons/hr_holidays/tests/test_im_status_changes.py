from datetime import timedelta

from odoo.addons.bus.tests.common import BusCase, BusResult
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.mail.tools.discuss import Store
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestImStatusChanges(TransactionCase, BusCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.absence_type = cls.env["hr.work.entry.type"].create(
            {
                "name": "Legal Leaves",
                "code": "Legal Leaves",
                "requires_allocation": False,
                "count_as": "absence",
                "request_unit": "hour",
                "unit_of_measure": "hour",
            }
        )
        cls.employee = cls._create_employee("im_status_leave")

    @classmethod
    def _create_employee(cls, login):
        user = mail_new_test_user(cls.env, login=login)
        return cls.env["hr.employee"].create({"name": login, "user_id": user.id})

    def _create_leave(self, employees, state="validate", work_entry_type=None):
        leaves = self.env["hr.leave"].create(
            [
                {
                    "request_date_from": "2026-10-27",
                    "request_date_to": "2026-10-27",
                    "request_hour_from": 10,
                    "request_hour_to": 11,
                    "employee_id": employee.id,
                    "work_entry_type_id": (work_entry_type or self.absence_type).id,
                }
                for employee in employees
            ]
        )
        leaves.write({"state": state})
        return leaves

    def _run_cron(self, since, until):
        with self.mock_datetime_and_now(until):
            self.env["res.users"].with_context(
                lastcall=since
            )._cron_send_im_status_changes()

    def _expected(self, employees, until):
        self.env.invalidate_all()
        with self.mock_datetime_and_now(until):
            return BusResult(
                (employees.user_id, "presence_internal"),
                "mail.record/insert",
                Store().add(employees, ["is_absent", "leave_date_to"]),
            )

    def _around(self, dt):
        return dt - timedelta(minutes=1), dt + timedelta(minutes=1)

    def test_leave_start_sends_absent(self):
        since, until = self._around(self._create_leave(self.employee).date_from)
        expected = self._expected(self.employee, until)
        self.assertTrue(expected.payload["hr.employee"][0]["is_absent"])
        with self.assertBus(expected):
            self._run_cron(since, until)

    def test_leave_end_sends_back(self):
        since, until = self._around(self._create_leave(self.employee).date_to)
        expected = self._expected(self.employee, until)
        self.assertFalse(expected.payload["hr.employee"][0]["is_absent"])
        with self.assertBus(expected):
            self._run_cron(since, until)

    def test_unvalidated_leave_ignored(self):
        leave = self._create_leave(self.employee, state="confirm")
        with self.assertBus([]):
            self._run_cron(*self._around(leave.date_from))

    def test_working_time_leave_ignored(self):
        working_time_type = self.absence_type.copy(
            {"count_as": "working_time", "elligible_for_accrual_rate": True}
        )
        leave = self._create_leave(self.employee, work_entry_type=working_time_type)
        with self.assertBus([]):
            self._run_cron(*self._around(leave.date_from))

    def _cron_trigger_times(self):
        cron = self.env.ref("mail.ir_cron_send_im_status_changes")
        return sorted(
            self.env["ir.cron.trigger"]
            .sudo()
            .search([("cron_id", "=", cron.id)])
            .mapped("call_at")
        )

    def test_next_change_is_leave_boundary(self):
        leave = self._create_leave(self.employee)
        next_change = self.env["res.users"]._get_next_im_status_change
        before = leave.date_from - timedelta(hours=1)
        self.assertEqual(next_change(before), leave.date_from)
        self.assertEqual(next_change(leave.date_from), leave.date_to)

    def test_validation_triggers_leave_boundaries(self):
        with self.mock_datetime_and_now("2026-10-27 00:00:00"):
            leave = self._create_leave(self.employee, state="confirm")
            self.env["ir.cron.trigger"].sudo().search([]).unlink()
            leave.write({"state": "validate"})
        self.assertEqual(
            self._cron_trigger_times(),
            [
                leave.date_from + timedelta(seconds=1),
                leave.date_to + timedelta(seconds=1),
            ],
        )

    def test_moving_leave_triggers_new_boundaries(self):
        with self.mock_datetime_and_now("2026-10-27 00:00:00"):
            leave = self._create_leave(self.employee)
            self.env["ir.cron.trigger"].sudo().search([]).unlink()
            leave.with_context(leave_skip_state_check=True).write(
                {"request_hour_from": 9, "request_hour_to": 10}
            )
        self.assertEqual(
            self._cron_trigger_times(),
            [
                leave.date_from + timedelta(seconds=1),
                leave.date_to + timedelta(seconds=1),
            ],
        )

    def test_validate_ongoing_leave_sends_absent(self):
        leave = self._create_leave(self.employee, state="confirm")
        now = leave.date_from + timedelta(minutes=30)
        with (
            self.mock_datetime_and_now(now),
            self.assertBus(lambda: self._expected(self.employee, now)),
        ):
            leave.write({"state": "validate"})
        expected = self._expected(self.employee, now)
        self.assertTrue(expected.payload["hr.employee"][0]["is_absent"])

    def test_edits_ending_ongoing_leave_send_back(self):
        for edit in (
            lambda leave: leave.unlink(),
            lambda leave: leave.write({"state": "refuse"}),
        ):
            with self.subTest(edit=edit):
                leave = self._create_leave(self.employee)
                now = leave.date_from + timedelta(minutes=30)
                with (
                    self.mock_datetime_and_now(now),
                    self.assertBus(lambda: self._expected(self.employee, now)),
                ):
                    edit(leave.with_context(leave_skip_state_check=True))
                expected = self._expected(self.employee, now)
                self.assertFalse(expected.payload["hr.employee"][0]["is_absent"])
