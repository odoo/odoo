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
        cls.user_c = cls.env["res.users"].create(
            {
                "name": "Kudos C",
                "login": "kudos_c",
                "group_ids": [
                    Command.link(cls.env.ref("base.group_user").id),
                    Command.link(
                        cls.env.ref("od19_recognition.group_recognition_user").id
                    ),
                ],
            }
        )
        cls.manager_user = cls.env["res.users"].create(
            {
                "name": "Kudos Manager",
                "login": "kudos_manager",
                "group_ids": [
                    Command.link(cls.env.ref("base.group_user").id),
                    Command.link(
                        cls.env.ref("od19_recognition.group_recognition_manager").id
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
        cls.emp_c = cls.env["hr.employee"].create(
            {"name": "Kudos C", "user_id": cls.user_c.id}
        )
        cls.emp_manager = cls.env["hr.employee"].create(
            {"name": "Kudos Manager", "user_id": cls.manager_user.id}
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

    def test_user_cannot_impersonate_author(self):
        with self.assertRaises(ValidationError):
            self.env["od19.recognition"].with_user(self.user_b).create(
                {
                    "author_id": self.emp_a.id,
                    "recipient_id": self.emp_b.id,
                    "message": "forged",
                }
            )

    def test_author_can_unlink_own(self):
        rec = self.env["od19.recognition"].with_user(self.user_a).create(
            {
                "author_id": self.emp_a.id,
                "recipient_id": self.emp_b.id,
                "message": "Thanks",
            }
        )
        rec.with_user(self.user_a).unlink()
        self.assertFalse(rec.exists())

    def test_non_author_cannot_unlink(self):
        rec = self.env["od19.recognition"].create(
            {
                "author_id": self.emp_a.id,
                "recipient_id": self.emp_b.id,
                "message": "Thanks",
            }
        )
        with self.assertRaises(AccessError):
            rec.with_user(self.user_b).unlink()

    def test_manager_can_moderate(self):
        rec = self.env["od19.recognition"].create(
            {
                "author_id": self.emp_a.id,
                "recipient_id": self.emp_b.id,
                "message": "Thanks",
            }
        )
        manager_rec = rec.with_user(self.manager_user)
        self.assertEqual(manager_rec.read(["message"])[0]["id"], rec.id)
        manager_rec.write({"message": "moderated"})
        self.assertEqual(rec.message, "moderated")
        manager_rec.unlink()
        self.assertFalse(rec.exists())

    def test_public_kudos_visible_to_others(self):
        public = self.env["od19.recognition"].create(
            {
                "author_id": self.emp_a.id,
                "recipient_id": self.emp_b.id,
                "message": "public shout-out",
                "is_public": True,
            }
        )
        private = self.env["od19.recognition"].create(
            {
                "author_id": self.emp_a.id,
                "recipient_id": self.emp_c.id,
                "message": "private note",
                "is_public": False,
            }
        )
        visible = (
            self.env["od19.recognition"].with_user(self.user_b).search([]).ids
        )
        self.assertIn(public.id, visible)
        self.assertNotIn(private.id, visible)
