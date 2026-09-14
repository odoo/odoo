from datetime import date

from psycopg.errors import NotNullViolation, UniqueViolation

from odoo.tests import tagged
from odoo.tools import mute_logger

from .common import HomeworkingCase


@tagged("post_install", "-at_install")
class TestEmployeeLocation(HomeworkingCase):
    def test_an_exception_names_itself(self):
        exception = self.set_exception(date(2025, 7, 9), self.work_office_1)
        self.assertEqual(
            exception.display_name, "Employee Test - Office 1 (2025-07-09)"
        )

    def test_an_exception_without_a_date_is_refused(self):
        with self.assertRaises(NotNullViolation), mute_logger("odoo.db.cursor"):
            self.env["hr.employee.location"].create(
                {
                    "employee_id": self.employee.id,
                    "work_location_id": self.work_home.id,
                }
            )

    def test_an_employee_has_at_most_one_exception_per_day(self):
        self.set_exception(date(2025, 7, 9), self.work_office_1)
        with self.assertRaises(UniqueViolation), mute_logger("odoo.db.cursor"):
            self.set_exception(date(2025, 7, 9), self.work_office_2)

    def test_the_employee_reaches_its_exceptions(self):
        exception = self.set_exception(date(2025, 7, 9), self.work_office_1)
        self.assertEqual(self.employee.location_ids, exception)
