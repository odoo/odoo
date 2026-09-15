from psycopg import IntegrityError

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestEmployeeResourceParty(TransactionCase):
    def test_a_new_employee_and_its_resource_are_one_party(self):
        employee = self.env["hr.employee"].create({"name": "One Party"})
        self.assertEqual(employee.resource_id.partner_id, employee.partner_id)
        self.assertEqual(
            self.env["res.partner"]
            .with_context(active_test=False)
            .search([("name", "=", "One Party")]),
            employee.partner_id,
        )

    def test_hiring_a_person_who_already_holds_a_resource_takes_it(self):
        contractor = self.env["res.partner"].create({"name": "Former Contractor"})
        (resource,) = contractor._get_or_create_resources(self.env.company)
        employee = self.env["hr.employee"].create(
            {"name": "Former Contractor", "partner_id": contractor.id}
        )
        self.assertEqual(employee.resource_id, resource)
        self.assertEqual(contractor.resource_ids, resource)

    def test_an_employee_on_a_resource_is_its_person(self):
        resource = self.env["resource.resource"].create({"name": "Booked First"})
        employee = self.env["hr.employee"].create({"resource_id": resource.id})
        self.assertEqual(employee.partner_id, resource.partner_id)
        self.assertEqual(employee.name, "Booked First")

    def test_a_copied_employee_is_a_new_person_with_one_resource(self):
        employee = self.env["hr.employee"].create({"name": "Template Hire"})
        copy = employee.copy()
        self.assertNotEqual(copy.partner_id, employee.partner_id)
        self.assertEqual(copy.resource_id.partner_id, copy.partner_id)
        self.assertFalse(
            self.env["res.partner"].search(
                [("name", "=like", "Template Hire%"), ("employee_ids", "=", False)]
            )
        )

    def test_a_person_is_one_employee_per_company(self):
        employee = self.env["hr.employee"].create({"name": "Hired Once"})
        with self.assertRaises(IntegrityError), self.cr.savepoint():
            self.env["hr.employee"].create(
                {"name": "Hired Once", "partner_id": employee.partner_id.id}
            )

    def test_leaving_a_shared_party_leaves_its_identifiers_and_keeps_it(self):
        shared = self.env["res.partner"].create({"name": "Generic Public"})
        company = self.env["res.company"].create({"name": "Second Payroll"})
        first = self.env["hr.employee"].create(
            {"name": "First Misbound", "partner_id": shared.id}
        )
        self.env["hr.employee"].create(
            {
                "name": "Second Misbound",
                "partner_id": shared.id,
                "company_id": company.id,
            }
        )
        first.ssnid = "999000111"
        own = self.env["res.partner"].create({"name": "First Misbound"})
        first.partner_id = own
        self.assertEqual(first.resource_id.partner_id, own)
        self.assertTrue(shared.active)
        self.assertIn("SSN", shared.identifier_ids.type_id.mapped("code"))
        self.assertFalse(own.identifier_ids)

    def test_leaving_an_own_party_carries_its_identifiers(self):
        employee = self.env["hr.employee"].create(
            {"name": "Moves Alone", "ssnid": "999000222"}
        )
        former = employee.partner_id
        employee.partner_id = self.env["res.partner"].create({"name": "Moves Alone"})
        self.assertEqual(employee.ssnid, "999000222")
        self.assertFalse(former.identifier_ids)
        self.assertFalse(former.active)

    def test_a_new_employees_timezone_is_the_one_given(self):
        employee = (
            self.env["hr.employee"]
            .with_context(tz="Asia/Tokyo")
            .create({"name": "Zoned Hire", "tz": "America/Lima"})
        )
        self.assertEqual(employee.resource_id.tz, "America/Lima")
        self.assertEqual(employee.partner_id.tz, "America/Lima")
