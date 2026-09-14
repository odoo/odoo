from datetime import timedelta

from odoo import Command, fields
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestAttendanceDrivenPresence(TransactionCase):
    """Who `hr_attendance` decides the presence state for, and on what evidence.

    The module holds two halves of one question. Being checked in is EVIDENCE
    that somebody is there, and it counts for every company. Being checked out
    during working hours is an INFERENCE from the absence of evidence, and it
    is only sound where the company asked for attendance to be its presence
    control -- `hr_presence_control_attendance`, the flag
    `_compute_presence_icon` has consulted all along.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.always_on = cls.env["resource.calendar"].create(
            {
                "name": "Round the clock",
                "tz": "UTC",
                "flexible_hours": False,
                "attendance_ids": [
                    Command.clear(),
                    *(
                        Command.create(
                            {
                                "name": f"day {day}",
                                "dayofweek": str(day),
                                "hour_from": 0,
                                "hour_to": 23.98,
                                "day_period": "morning",
                            }
                        )
                        for day in range(7)
                    ),
                ],
            }
        )

    def _employee(self, *, attendance_control, login_control=False, checked_in=False):
        company = self.env["res.company"].create(
            {
                "name": f"attendance={attendance_control} login={login_control}",
                "hr_presence_control_attendance": attendance_control,
                "hr_presence_control_login": login_control,
            }
        )
        company.resource_calendar_id = self.always_on.copy({"company_id": company.id})
        employee = self.env["hr.employee"].create(
            {"name": "Subject", "company_id": company.id, "tz": "UTC"}
        )
        employee.resource_id.tz = "UTC"
        if checked_in:
            self.env["hr.attendance"].create(
                {
                    "employee_id": employee.id,
                    "check_in": fields.Datetime.now() - timedelta(hours=1),
                }
            )
        self.env.flush_all()
        self.env.invalidate_all()
        return employee

    def test_the_fixture_puts_the_employee_inside_working_hours(self):
        employee = self._employee(attendance_control=True)
        self.assertIn(
            employee.id,
            employee._get_employee_ids_working_now(),
            "every assertion below is about an employee who is expected at "
            "work right now; if the fixture stops saying so they all pass "
            "against a schedule nobody is scheduled in",
        )

    def test_checked_in_is_present_even_without_attendance_control(self):
        employee = self._employee(attendance_control=False, checked_in=True)
        self.assertEqual(
            employee.hr_presence_state,
            "present",
            "an attendance record is somebody at the kiosk. Gating this half "
            "too made a checked-in employee read Absent wherever "
            "hr_presence_control_login was on, because hr then judged them by "
            "a user session they did not have.",
        )

    def test_checked_in_is_present_with_attendance_control(self):
        employee = self._employee(attendance_control=True, checked_in=True)
        self.assertEqual(employee.hr_presence_state, "present")

    def test_checked_in_is_present_even_alongside_login_control(self):
        employee = self._employee(
            attendance_control=False, login_control=True, checked_in=True
        )
        self.assertEqual(
            employee.hr_presence_state,
            "present",
            "the cell the symmetric gate broke",
        )

    def test_absence_is_inferred_only_where_the_company_asked(self):
        asked = self._employee(attendance_control=True)
        self.assertEqual(
            asked.hr_presence_state,
            "absent",
            "expected at work, no attendance: the company asked for this",
        )

    def test_absence_is_not_inferred_where_the_company_did_not_ask(self):
        not_asked = self._employee(attendance_control=False)
        self.assertNotEqual(
            not_asked.hr_presence_state,
            "absent",
            "a company that did not make attendance its presence control has "
            "not said that no attendance means absent",
        )

    def test_the_icon_and_the_state_read_the_same_flag(self):
        """They disagreed: the icon consulted the flag, the state did not."""
        for control in (True, False):
            with self.subTest(attendance_control=control):
                employee = self._employee(attendance_control=control)
                self.assertEqual(
                    employee.show_hr_icon_display,
                    control or bool(employee.user_id),
                    "`_compute_presence_icon` gates on "
                    "hr_presence_control_attendance; the state now does too",
                )
