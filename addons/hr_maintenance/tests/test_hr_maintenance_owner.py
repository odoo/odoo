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

    def test_an_internal_user_without_employee_can_create_a_request(self):
        request = (
            self.env["maintenance.request"]
            .with_user(self.requester)
            .create({"name": "Printer jammed"})
        )
        self.assertEqual(request.owner_user_id, self.requester)
        self.assertFalse(request.user_id)

    def test_an_employee_assigned_equipment_makes_its_user_the_owner(self):
        equipment = self.env["maintenance.equipment"].create(
            {"name": "Laptop", "employee_id": self.sender_employee.id}
        )
        request = self.env["maintenance.request"].create(
            {
                "name": "Battery",
                "equipment_id": equipment.id,
                "employee_id": self.sender_employee.id,
            }
        )
        self.assertEqual(request.owner_user_id, self.sender)

    def test_an_explicit_equipment_owner_is_kept(self):
        for assign_to in ("employee", "other"):
            with self.subTest(assign_to=assign_to):
                equipment = self.env["maintenance.equipment"].create(
                    {
                        "name": f"Owned {assign_to}",
                        "equipment_assign_to": assign_to,
                        "owner_user_id": self.requester.id,
                    }
                )
                self.assertEqual(equipment.owner_user_id, self.requester)

    def test_a_request_by_email_belongs_to_the_sender_employee(self):
        request = self.env["maintenance.request"].message_new(
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
        self.assertEqual(request.employee_id, self.sender_employee)
