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

    def _elsewhere(self):
        company = self.env["res.company"].create({"name": "Elsewhere"})
        location = self.env["hr.work.location"].create(
            {
                "name": "Elsewhere office",
                "location_type": "office",
                "address_id": self.address.id,
                "company_id": company.id,
            }
        )
        employee = self.env["hr.employee"].create(
            {"name": "Elsewhere worker", "company_id": company.id}
        )
        exception = self.set_exception(date(2025, 7, 9), location, employee=employee)
        return company, employee, exception

    def _local_hr_user(self):
        return self.env["res.users"].create(
            {
                "name": "Local HR",
                "login": "local_hr_user",
                "company_id": self.env.company.id,
                "company_ids": [(6, 0, self.env.company.ids)],
                "group_ids": [(4, self.env.ref("hr.group_hr_user").id)],
            }
        )

    def test_an_exception_does_not_leak_across_companies(self):
        # hr.employee's own rules hide an employee of another company; without a
        # company on the exception, its `employee_name` related handed the same
        # name straight back, and the record was writable too.
        _company, employee, exception = self._elsewhere()
        as_local_hr = self.env(user=self._local_hr_user(), su=False)

        self.assertFalse(
            self.env["hr.employee"]
            .with_env(as_local_hr)
            .search([("id", "=", employee.id)]),
            "the employee itself is already hidden",
        )
        self.assertFalse(
            self.env["hr.employee.location"]
            .with_env(as_local_hr)
            .search([("id", "=", exception.id)]),
            "so their exceptional location must be too",
        )

    def test_an_exception_carries_its_employees_company(self):
        company, _employee, exception = self._elsewhere()
        self.assertEqual(exception.company_id, company)
