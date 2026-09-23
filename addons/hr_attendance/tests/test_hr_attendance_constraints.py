import time

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("attendance_constraints")
class TestHrAttendance(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.attendance = cls.env["hr.attendance"]
        cls.test_employee = cls.env["hr.employee"].create(
            {"name": "Jacky", "ruleset_id": False}
        )
        cls.open_attendance = cls.attendance.create(
            {
                "employee_id": cls.test_employee.id,
                "check_in": time.strftime("%Y-%m-10 10:00"),
            }
        )
        # `open_attendance` runs from 10:00 to whenever the employee checks out,
        # which is to say it occupies the rest of time. Tests that are not about
        # that need an employee who is not still checked in.
        cls.other_employee = cls.env["hr.employee"].create(
            {"name": "Sully", "ruleset_id": False}
        )

    def test_attendance_in_before_out(self):
        with self.assertRaises(ValidationError):
            self.attendance.create(
                {
                    "employee_id": self.other_employee.id,
                    "check_in": time.strftime("%Y-%m-10 12:00"),
                    "check_out": time.strftime("%Y-%m-10 11:00"),
                }
            )

    def test_attendance_no_check_out(self):
        with self.assertRaises(ValidationError):
            self.attendance.create(
                {
                    "employee_id": self.test_employee.id,
                    "check_in": time.strftime("%Y-%m-10 11:00"),
                }
            )

    def test_attendance_1(self):
        self.attendance.create(
            {
                "employee_id": self.test_employee.id,
                "check_in": time.strftime("%Y-%m-10 07:30"),
                "check_out": time.strftime("%Y-%m-10 09:00"),
            }
        )
        with self.assertRaises(ValidationError):
            self.attendance.create(
                {
                    "employee_id": self.test_employee.id,
                    "check_in": time.strftime("%Y-%m-10 08:30"),
                    "check_out": time.strftime("%Y-%m-10 09:30"),
                }
            )

    def test_an_attendance_cannot_be_created_around_an_open_one(self):
        """The employee is still checked in from 10:00.

        A completed 11:00-12:00 attendance says they were also somewhere else,
        finished. Accepting it stores a state that only fails later, when the
        open attendance is finally checked out and overlaps it.
        """
        with self.assertRaises(ValidationError):
            self.attendance.create(
                {
                    "employee_id": self.test_employee.id,
                    "check_in": time.strftime("%Y-%m-10 11:00"),
                    "check_out": time.strftime("%Y-%m-10 12:00"),
                }
            )

    def test_an_attendance_cannot_be_extended_over_a_later_one(self):
        """The constraint has to hold on write, not only on create."""
        first = self.attendance.create(
            {
                "employee_id": self.other_employee.id,
                "check_in": time.strftime("%Y-%m-10 08:00"),
                "check_out": time.strftime("%Y-%m-10 09:00"),
            }
        )
        self.attendance.create(
            {
                "employee_id": self.other_employee.id,
                "check_in": time.strftime("%Y-%m-10 11:00"),
                "check_out": time.strftime("%Y-%m-10 12:00"),
            }
        )
        with self.assertRaises(ValidationError):
            first.write({"check_out": time.strftime("%Y-%m-10 11:30")})

    def test_reopening_an_attendance_that_has_a_successor_is_refused(self):
        """Clearing `check_out` makes the attendance open-ended, which would
        swallow every attendance recorded after it."""
        first = self.attendance.create(
            {
                "employee_id": self.other_employee.id,
                "check_in": time.strftime("%Y-%m-10 08:00"),
                "check_out": time.strftime("%Y-%m-10 09:00"),
            }
        )
        self.attendance.create(
            {
                "employee_id": self.other_employee.id,
                "check_in": time.strftime("%Y-%m-10 11:00"),
                "check_out": time.strftime("%Y-%m-10 12:00"),
            }
        )
        with self.assertRaises(ValidationError):
            first.write({"check_out": False})

    def test_time_format_attendance(self):
        self.env.user.tz = "UTC"
        self.env["res.lang"]._activate_lang("en_US")
        lang = self.env["res.lang"]._get_lang_cached(self.env.user.lang)
        lang.time_format = "%I:%M:%S %p"
        attendance_id = self.attendance.create(
            {
                "employee_id": self.other_employee.id,
                "check_in": time.strftime("%Y-%m-28 08:00"),
                "check_out": time.strftime("%Y-%m-28 09:00"),
            }
        )
        self.assertEqual(attendance_id.display_name, "01:00 (08:00:00 AM-09:00:00 AM)")
        lang.time_format = "%H:%M:%S"
        attendance_id._compute_display_name()
        self.assertEqual(attendance_id.display_name, "01:00 (08:00:00-09:00:00)")
