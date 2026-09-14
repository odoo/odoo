from datetime import date

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestWorkLocation(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.employee = cls.env["hr.employee"].create({"name": "HWC employee"})
        cls.location = cls.env["hr.work.location"].create(
            {
                "name": "HWC home",
                "location_type": "home",
                "address_id": cls.env.company.partner_id.id,
            }
        )

    def test_worklocation_base_structure(self):
        data = self.employee._get_worklocation(date(2026, 1, 5), date(2026, 1, 11))
        entry = data[self.employee.id]
        self.assertEqual(entry["employee_id"], self.employee.id)
        self.assertEqual(entry["employee_name"], "HWC employee")
        for day in ("monday_location_id", "sunday_location_id"):
            self.assertIn(day, entry)
            self.assertIn("location_type", entry[day])

    def test_worklocation_includes_period_exceptions(self):
        self.env["hr.employee.location"].create(
            {
                "employee_id": self.employee.id,
                "work_location_id": self.location.id,
                "date": date(2026, 1, 7),
            }
        )
        data = self.employee._get_worklocation(date(2026, 1, 5), date(2026, 1, 11))
        entry = data[self.employee.id]
        self.assertIn("exceptions", entry)
        self.assertIn("2026-01-07", entry["exceptions"])
        self.assertEqual(
            entry["exceptions"]["2026-01-07"]["work_location_id"], self.location.id
        )

    def test_worklocation_no_exceptions_outside_range(self):
        self.env["hr.employee.location"].create(
            {
                "employee_id": self.employee.id,
                "work_location_id": self.location.id,
                "date": date(2026, 2, 20),
            }
        )
        data = self.employee._get_worklocation(date(2026, 1, 5), date(2026, 1, 11))
        self.assertNotIn("exceptions", data[self.employee.id])

    def test_the_calendar_covers_every_allowed_company(self):
        # The lookup filtered on env.company, so an employee in a second allowed
        # company vanished from the calendar of a user who had both enabled.
        other = self.env["res.company"].create({"name": "Second"})
        partner = self.env["res.partner"].create({"name": "Elsewhere worker"})
        self.env["hr.employee"].create(
            {
                "name": "Elsewhere worker",
                "company_id": other.id,
                "partner_id": partner.id,
            }
        )
        both = self.env.companies | other
        data = partner.with_context(allowed_company_ids=both.ids).get_worklocation(
            date(2026, 1, 5), date(2026, 1, 11)
        )
        self.assertTrue(data, "an employee of an allowed company must be covered")
