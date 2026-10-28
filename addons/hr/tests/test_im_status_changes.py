from datetime import datetime

from odoo.addons.bus.tests.common import BusCase, BusResult
from odoo.addons.hr.tests.common import TestHrCommon
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.mail.tools.discuss import Store
from odoo.tests import tagged


def dt(hour, minute=0):
    # a Tuesday
    return datetime(2026, 10, 27, hour, minute)


@tagged("post_install", "-at_install")
class TestImStatusChanges(TestHrCommon, BusCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.calendar = cls.env.company.resource_calendar_id
        cls.env["hr.employee"].search([]).user_id = False
        cls.employee_a = cls._create_employee("im_status_a")

    @classmethod
    def _create_employee(cls, login, **vals):
        user = mail_new_test_user(cls.env, login=login)
        return cls.env["hr.employee"].create(
            {
                "name": login,
                "user_id": user.id,
                "tz": "UTC",
                "resource_calendar_id": cls.calendar.id,
                **vals,
            }
        )

    def _run_cron(self, since, until):
        with self.mock_datetime_and_now(until):
            self.env["res.users"].with_context(
                lastcall=since
            )._cron_send_im_status_changes()

    def _expected(self, employees, value):
        return BusResult(
            (employees.user_id, "presence_internal"),
            "mail.record/insert",
            Store().add(employees, {"is_off_hours": value}),
        )

    def test_work_start_sends_false(self):
        with self.assertBus(self._expected(self.employee_a, False)):
            self._run_cron(dt(6, 59), dt(7, 1))

    def test_lunch_sends_nothing(self):
        with self.assertBus([]):
            self._run_cron(dt(11, 59), dt(12, 1))

    def test_work_end_sends_true(self):
        with self.assertBus(self._expected(self.employee_a, True)):
            self._run_cron(dt(16, 59), dt(17, 1))

    def test_sent_value_matches_compute(self):
        for since, until in [(dt(6, 59), dt(7, 1)), (dt(16, 59), dt(17, 1))]:
            self.env.invalidate_all()
            with self.mock_datetime_and_now(until):
                is_off_hours = self.employee_a.is_off_hours
            with self.assertBus(self._expected(self.employee_a, is_off_hours)):
                self._run_cron(since, until)

    def test_user_with_two_employees(self):
        company_2 = self.env["res.company"].create({"name": "Company 2"})
        night_calendar = self.env["resource.calendar"].create(
            {
                "name": "Nights",
                "company_id": company_2.id,
                "attendance_ids": [
                    (0, 0, {"dayofweek": "1", "hour_from": 20, "hour_to": 23})
                ],
            }
        )
        self.employee_a.user_id.company_ids += company_2
        employee_b = self.env["hr.employee"].create(
            {
                "name": "im_status_a night",
                "user_id": self.employee_a.user_id.id,
                "company_id": company_2.id,
                "tz": "UTC",
                "resource_calendar_id": night_calendar.id,
            }
        )
        with self.assertBus(self._expected(self.employee_a, False)):
            self._run_cron(dt(6, 59), dt(7, 1))
        with self.assertBus(self._expected(employee_b, False)):
            self._run_cron(dt(18, 59), dt(19, 1))

    def test_skips_incomplete(self):
        self.env["hr.employee"].create(
            {"name": "no user", "tz": "UTC", "resource_calendar_id": self.calendar.id}
        )
        with self.assertBus(self._expected(self.employee_a, False)):
            self._run_cron(dt(6, 59), dt(7, 1))

    def test_next_change_is_next_schedule_edge(self):
        next_change = self.env["res.users"]._get_next_im_status_change
        self.assertEqual(next_change(dt(6)), dt(7))
        self.assertEqual(next_change(dt(7, 30)), dt(12))
        self.assertEqual(next_change(dt(12)), dt(17))
        friday_evening = datetime(2026, 10, 30, 17, 30)
        self.assertEqual(next_change(friday_evening), datetime(2026, 11, 2, 7))
