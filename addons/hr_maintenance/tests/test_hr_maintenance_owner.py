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
