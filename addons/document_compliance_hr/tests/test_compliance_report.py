from odoo.addons.document_compliance.tests.common import ComplianceCase


class TestComplianceReportEmployees(ComplianceCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["document.type"].search([("is_mandatory", "=", True)]).write(
            {"is_mandatory": False}
        )
        cls.employee_type = cls._type(
            "SCOPE_EMPLOYEE", is_mandatory=True, applies_to="hr.employee"
        )
        cls.partner_type = cls._type(
            "SCOPE_PARTNER_ONLY", is_mandatory=True, applies_to="res.partner"
        )

    def test_employees_are_an_entity_a_type_can_apply_to(self):
        selection = dict(self.env["document.type"]._selection_applies_to())

        self.assertIn("hr.employee", selection)

    def test_an_employee_is_held_only_to_employee_types(self):
        employee = self.env["hr.employee"].create({"name": "Reported Employee"})
        self._doc(
            self.employee_type,
            365,
            name="Badge",
            res_model="hr.employee",
            res_id=employee.id,
        )
        self._publish()

        row = self.env["document.compliance.report"].search(
            [("entity_type", "=", "hr.employee"), ("entity_id", "=", employee.id)]
        )

        self.assertEqual(row.entity_name, "Reported Employee")
        self.assertEqual((row.total_required, row.total_valid), (1, 1))
        self.assertEqual(row.compliance_state, "compliant")
