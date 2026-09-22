from datetime import UTC, datetime
from unittest.mock import patch

from odoo import fields
from odoo.libs.datetime import timezone
from odoo.tests import Form, new_test_user
from odoo.tests.common import TransactionCase, tagged


@tagged("attendance_process")
class TestHrAttendance(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = new_test_user(cls.env, login="fru", groups="base.group_user")
        cls.user_no_pin = new_test_user(cls.env, login="gru", groups="base.group_user")
        cls.test_employee = cls.env["hr.employee"].create(
            {
                "name": "François Russie",
                "user_id": cls.user.id,
                "pin": "1234",
                "ruleset_id": False,
            }
        )
        cls.employee_kiosk = cls.env["hr.employee"].create(
            {
                "name": "Machiavel",
                "pin": "5678",
            }
        )

    def setUp(self):
        super().setUp()
        (self.test_employee | self.employee_kiosk).last_attendance_id.unlink()

    def test_employee_state(self):
        assert self.test_employee.attendance_state == "checked_out"
        self.test_employee._attendance_action_change()
        assert self.test_employee.attendance_state == "checked_in"
        self.test_employee._attendance_action_change()
        assert self.test_employee.attendance_state == "checked_out"

    def test_employee_group_id(self):
        self.env["hr.attendance"].create(
            {
                "employee_id": self.employee_kiosk.id,
                "check_in": "2025-08-01 08:00:00",
                "check_out": "2025-08-01 17:00:00",
            }
        )
        context = self.env.context.copy()
        context["read_group_expand"] = True

        groups = (
            self.env["hr.attendance"]
            .with_context(**context)
            .web_read_group(domain=[], groupby=["employee_id"])
        )
        groups = groups["groups"]

        grouped_employee_ids = [g["employee_id"][0] for g in groups]

        self.assertNotIn(self.test_employee.id, grouped_employee_ids)
        self.assertIn(self.employee_kiosk.id, grouped_employee_ids)

        context["gantt_start_date"] = fields.Datetime.now()
        context["allowed_company_ids"] = [self.env.company.id]

        groups = (
            self.env["hr.attendance"]
            .with_context(**context)
            .web_read_group(domain=[], groupby=["employee_id"])
        )
        groups = groups["groups"]

        grouped_employee_ids = [g["employee_id"][0] for g in groups]

        self.assertIn(self.test_employee.id, grouped_employee_ids)
        self.assertIn(self.employee_kiosk.id, grouped_employee_ids)

    def test_hours_today(self):
        def tz_datetime(year, month, day, hour, minute):
            tz = timezone("Europe/Brussels")
            return (
                datetime(year, month, day, hour, minute)
                .replace(tzinfo=tz)
                .astimezone(UTC)
                .replace(tzinfo=None)
            )

        employee = self.env["hr.employee"].create(
            {"name": "Cunégonde", "tz": "Europe/Brussels"}
        )
        self.env["hr.attendance"].create(
            {
                "employee_id": employee.id,
                "check_in": tz_datetime(2019, 3, 1, 22, 0),
                "check_out": tz_datetime(2019, 3, 2, 2, 0),
            }
        )
        self.env["hr.attendance"].create(
            {
                "employee_id": employee.id,
                "check_in": tz_datetime(2019, 3, 2, 11, 0),
            }
        )

        with patch.object(
            fields.Datetime,
            "now",
            lambda: tz_datetime(2019, 3, 2, 14, 0).astimezone(UTC).replace(tzinfo=None),
        ):
            self.assertEqual(employee.hours_today, 5, "It should have counted 5 hours")

    def test_remove_check_in_value_from_attendance(self):
        attendance_form = Form(self.env["hr.attendance"])
        attendance_form.employee_id = self.test_employee
        attendance_form.check_in = False
        with self.assertRaises(AssertionError):
            attendance_form.save()

    def test_group_attendances_by_weekday(self):
        """Attendances can be grouped by the weekday they were worked on.

        `date` is stored, but nothing derived the weekday from it, so a manager
        could not separate Saturday work from weekday work without exporting
        and pivoting by hand.
        """
        # `_schedule_tz` reads the version's own `tz` ahead of the calendar's,
        # so pinning the employee is what fixes which day `date` lands on.
        self.employee_kiosk.tz = "UTC"
        self.env["hr.attendance"].create(
            [
                {
                    "employee_id": self.employee_kiosk.id,
                    "check_in": "2025-08-01 08:00:00",  # a Friday
                    "check_out": "2025-08-01 17:00:00",
                },
                {
                    "employee_id": self.employee_kiosk.id,
                    "check_in": "2025-08-02 08:00:00",  # a Saturday
                    "check_out": "2025-08-02 12:00:00",
                },
                {
                    "employee_id": self.employee_kiosk.id,
                    "check_in": "2025-08-08 08:00:00",  # the next Friday
                    "check_out": "2025-08-08 17:00:00",
                },
            ]
        )

        count_by_weekday = dict(
            self.env["hr.attendance"]._read_group(
                [("employee_id", "=", self.employee_kiosk.id)],
                groupby=["day_of_date"],
                aggregates=["__count"],
            )
        )
        self.assertEqual(count_by_weekday, {"4": 2, "5": 1})

    def test_attendance_carries_the_working_schedule(self):
        """The employee's schedule is reachable from the attendance itself, so
        attendances can be searched and grouped by it."""
        attendance = self.env["hr.attendance"].create(
            {
                "employee_id": self.employee_kiosk.id,
                "check_in": "2025-08-01 08:00:00",
                "check_out": "2025-08-01 17:00:00",
            }
        )
        self.assertEqual(
            attendance.resource_calendar_id,
            self.employee_kiosk.resource_calendar_id,
        )
        self.assertIn(
            attendance,
            self.env["hr.attendance"].search(
                [
                    (
                        "resource_calendar_id",
                        "=",
                        self.employee_kiosk.resource_calendar_id.id,
                    ),
                ]
            ),
        )

    def test_extra_hours_analysis_report(self):
        """The Extra Hours Analysis report compiles and aggregates lines.

        Extra hours were only visible one attendance at a time; there was no
        action, and no list/pivot/graph, over `hr.attendance.overtime.line`.
        """
        Line = self.env["hr.attendance.overtime.line"]
        action = self.env.ref("hr_attendance.hr_attendance_overtime_analysis_action")
        self.assertEqual(action.res_model, "hr.attendance.overtime.line")

        for xmlid, view_type in [
            ("hr_attendance_overtime_analysis_view_list", "list"),
            ("hr_attendance_overtime_analysis_view_pivot", "pivot"),
            ("hr_attendance_overtime_analysis_view_graph", "graph"),
            ("hr_attendance_overtime_analysis_view_filter", "search"),
        ]:
            view = self.env.ref(f"hr_attendance.{xmlid}")
            self.assertTrue(Line.get_view(view.id, view_type)["arch"])

        Line.create(
            [
                {
                    "employee_id": self.employee_kiosk.id,
                    "date": "2025-08-01",
                    "duration": 2,
                },
                {
                    "employee_id": self.employee_kiosk.id,
                    "date": "2025-08-02",
                    "duration": 3,
                },
            ]
        )
        totals = dict(
            Line._read_group(
                [("employee_id", "=", self.employee_kiosk.id)],
                groupby=["employee_id"],
                aggregates=["duration:sum"],
            )
        )
        self.assertEqual(totals[self.employee_kiosk], 5)

    def test_open_the_attendance_behind_an_extra_hours_line(self):
        """The report's row button opens the attendance the line came from."""
        attendance = self.env["hr.attendance"].create(
            {
                "employee_id": self.employee_kiosk.id,
                "check_in": "2025-08-01 08:00:00",
                "check_out": "2025-08-01 20:00:00",
            }
        )
        line = self.env["hr.attendance.overtime.line"].create(
            {
                "employee_id": self.employee_kiosk.id,
                "date": "2025-08-01",
                "duration": 2,
                "attendance_id": attendance.id,
            }
        )
        action = line.action_open_linked_attendance()
        self.assertEqual(action["res_model"], "hr.attendance")
        self.assertEqual(action["res_id"], attendance.id)
