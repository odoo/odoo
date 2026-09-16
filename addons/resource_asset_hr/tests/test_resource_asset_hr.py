from datetime import timedelta

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase


class TestAssetCustody(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.employee = cls.env["hr.employee"].create({"name": "Custodian"})
        cls.department = cls.env["hr.department"].create({"name": "Workshop"})
        cls.laptop = cls.env["resource.asset"].create(
            {"name": "Laptop", "kind_id": cls.env.ref("resource_asset.kind_it").id}
        )

    def _assign(self, **vals):
        return self.env["resource.assignment"].create(
            {"resource_id": self.laptop.resource_id.id, "custody_role": "custodian", **vals}
        )

    def test_an_employee_holds_the_assets_assigned_to_them(self):
        self._assign(assignee_id=self.employee.resource_id.id)
        self.assertEqual(self.employee.asset_ids, self.laptop)
        self.assertEqual(self.employee.asset_count, 1)

    def test_a_department_holds_an_asset_without_a_person(self):
        assignment = self._assign(department_id=self.department.id)
        self.assertIn("Workshop", assignment.name)
        with self.assertRaises(ValidationError):
            self._assign()
        with self.assertRaises(ValidationError):
            self._assign(
                assignee_id=self.employee.resource_id.id,
                department_id=self.department.id,
            )

    def test_a_departure_releases_what_the_employee_holds(self):
        assignment = self._assign(
            assignee_id=self.employee.resource_id.id,
            date_start=fields.Datetime.now() - timedelta(days=3),
        )
        wizard = self.env["hr.departure.wizard"].create(
            {
                "employee_ids": [(6, 0, self.employee.ids)],
                "departure_reason_id": self.env["hr.departure.reason"]
                .search([], limit=1)
                .id,
            }
        )
        wizard.action_register_departure()
        self.assertTrue(assignment.date_end)
        self.employee.invalidate_recordset(["asset_ids"])
        self.assertFalse(self.employee.asset_ids)


class TestEmployeeCustody(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.employee = cls.env["hr.employee"].create({"name": "Holder"})
        cls.kind = cls.env.ref("resource_asset.kind_tool")

    def test_naming_the_operator_by_employee_writes_the_assignment(self):
        asset = self.env["resource.asset"].create(
            {
                "name": "Drill",
                "kind_id": self.kind.id,
                "operator_employee_id": self.employee.id,
            }
        )
        self.assertEqual(asset.operator_id, self.employee.resource_id)
        assignment = asset.assignment_ids.filtered(lambda a: a.custody_role == "operator")
        self.assertEqual(assignment.assignee_id, self.employee.resource_id)
        self.assertEqual(asset.operator_employee_id, self.employee)
        self.assertIn(
            asset,
            self.env["resource.asset"].search(
                [("operator_employee_id", "=", self.employee.id)]
            ),
        )
