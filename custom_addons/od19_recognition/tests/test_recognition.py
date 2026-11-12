from odoo import Command, http
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import HttpCase, TransactionCase, tagged


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


@tagged("post_install", "-at_install")
class TestRecognitionPortal(HttpCase):
    def setUp(self):
        super().setUp()
        self.giver = self.env["res.users"].create(
            {
                "name": "Feed Giver",
                "login": "feed_giver",
                "password": "feed_giver",
                "group_ids": [
                    Command.link(self.env.ref("base.group_user").id),
                    Command.link(
                        self.env.ref("od19_recognition.group_recognition_user").id
                    ),
                ],
            }
        )
        self.receiver = self.env["res.users"].create(
            {
                "name": "Feed Receiver",
                "login": "feed_receiver",
                "password": "feed_receiver",
                "group_ids": [
                    Command.link(self.env.ref("base.group_user").id),
                    Command.link(
                        self.env.ref("od19_recognition.group_recognition_user").id
                    ),
                ],
            }
        )
        self.emp_giver = self.env["hr.employee"].create(
            {"name": "Feed Giver", "user_id": self.giver.id}
        )
        self.emp_receiver = self.env["hr.employee"].create(
            {"name": "Feed Receiver", "user_id": self.receiver.id}
        )

    def test_summary_route_returns_json(self):
        self.authenticate("feed_giver", "feed_giver")
        response = self.url_open("/my/recognition/summary")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("feed", payload)
        self.assertIn("celebrations", payload)

    def test_give_route_creates_kudos_and_forces_author(self):
        self.authenticate("feed_giver", "feed_giver")
        self.url_open(
            "/my/recognition/give",
            data={
                "recipient_id": self.emp_receiver.id,
                "message": "Great work today",
                "csrf_token": http.Request.csrf_token(self),
            },
            allow_redirects=False,
        )
        created = self.env["od19.recognition"].search(
            [("recipient_id", "=", self.emp_receiver.id)], limit=1
        )
        self.assertTrue(created)
        self.assertEqual(created.author_id, self.emp_giver)
