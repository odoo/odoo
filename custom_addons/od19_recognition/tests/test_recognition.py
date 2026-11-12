from odoo import Command
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestRecognitionRules(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.badge = cls.env["od19.recognition.badge"].create({"name": "Thank You"})
        cls.user_a = cls.env["res.users"].create(
            {
                "name": "Kudos A",
                "login": "kudos_a",
                "group_ids": [
                    Command.link(cls.env.ref("base.group_user").id),
                    Command.link(
                        cls.env.ref("od19_recognition.group_recognition_user").id
                    ),
                ],
            }
        )
        cls.user_b = cls.env["res.users"].create(
            {
                "name": "Kudos B",
                "login": "kudos_b",
                "group_ids": [
                    Command.link(cls.env.ref("base.group_user").id),
                    Command.link(
                        cls.env.ref("od19_recognition.group_recognition_user").id
                    ),
                ],
            }
        )
        cls.emp_a = cls.env["hr.employee"].create(
            {"name": "Kudos A", "user_id": cls.user_a.id}
        )
        cls.emp_b = cls.env["hr.employee"].create(
            {"name": "Kudos B", "user_id": cls.user_b.id}
        )

    def test_create_forces_company(self):
        rec = (
            self.env["od19.recognition"]
            .with_user(self.user_a)
            .create(
                {
                    "author_id": self.emp_a.id,
                    "recipient_id": self.emp_b.id,
                    "badge_id": self.badge.id,
                    "message": "Great job!",
                }
            )
        )
        self.assertEqual(rec.company_id, self.user_a.company_id)

    def test_cannot_kudos_self(self):
        with self.assertRaises(ValidationError):
            self.env["od19.recognition"].create(
                {
                    "author_id": self.emp_a.id,
                    "recipient_id": self.emp_a.id,
                    "message": "Me",
                }
            )

    def test_message_length_limit(self):
        with self.assertRaises(ValidationError):
            self.env["od19.recognition"].create(
                {
                    "author_id": self.emp_a.id,
                    "recipient_id": self.emp_b.id,
                    "message": "x" * 501,
                }
            )

    def test_only_author_can_edit(self):
        rec = self.env["od19.recognition"].create(
            {
                "author_id": self.emp_a.id,
                "recipient_id": self.emp_b.id,
                "message": "Thanks",
            }
        )
        with self.assertRaises(AccessError):
            rec.with_user(self.user_b).write({"message": "hacked"})

    def test_private_kudos_hidden_from_others(self):
        private = self.env["od19.recognition"].create(
            {
                "author_id": self.emp_a.id,
                "recipient_id": self.emp_b.id,
                "message": "private note",
                "is_public": False,
            }
        )
        visible = (
            self.env["od19.recognition"].with_user(self.user_b).search([]).ids
        )
        self.assertNotIn(private.id, visible)
