from datetime import timedelta

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase


class TestHrMaintenanceOwner(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        group_user = cls.env.ref("base.group_user")
        cls.requester = cls.env["res.users"].create(
            {
                "name": "Requester without employee",
                "login": "hr_maintenance_requester",
                "group_ids": [(6, 0, [group_user.id])],
            }
        )
        cls.sender = cls.env["res.users"].create(
            {
                "name": "Mail sender",
                "login": "sender@example.com",
                "email": "sender@example.com",
                "group_ids": [(6, 0, [group_user.id])],
            }
        )
        cls.sender_employee = cls.env["hr.employee"].create(
            {"name": "Mail sender", "user_id": cls.sender.id}
        )

    def test_an_internal_user_without_employee_can_create_a_order(self):
        order = (
            self.env["maintenance.order"]
            .with_user(self.requester)
            .create({"name": "Printer jammed"})
        )
        self.assertEqual(order.owner_user_id, self.requester)
        self.assertFalse(order.user_id)

    def test_the_order_employee_user_is_the_owner(self):
        order = self.env["maintenance.order"].create(
            {"name": "Battery", "employee_id": self.sender_employee.id}
        )
        self.assertEqual(order.owner_user_id, self.sender)

    def test_a_order_by_email_belongs_to_the_sender_employee(self):
        order = self.env["maintenance.order"].message_new(
            {
                "from": "Mail sender <sender@example.com>",
                "email_from": "sender@example.com",
                "subject": "Screen flickers",
                "body": "It flickers.",
                "to": "",
                "cc": "",
                "message_id": "<hr-maintenance-owner@example.com>",
                "author_id": self.sender.partner_id.id,
            }
        )
        self.assertEqual(order.employee_id, self.sender_employee)


class TestHrMaintenanceCustody(TransactionCase):
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
            {"resource_id": self.laptop.resource_id.id, "role": "custodian", **vals}
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
