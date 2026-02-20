from odoo.addons.mail.tests.common import MailCase
from odoo.addons.website_forum.tests.common import TestForumCommon
from odoo.tests import users


class TestForumNotification(MailCase, TestForumCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.user_employee.karma = 100

        cls.partner_1, cls.partner_2, cls.partner_3 = cls.env["res.partner"].create(
            [
                {"name": "Partner", "email": "partner_1@example.com"},
                {"name": "Partner", "email": "partner_2@example.com"},
                {"name": "Partner", "email": "partner_3@example.com"},
            ]
        )

        cls.post.follower_ids = cls.partner_1
        cls.answer.follower_ids = cls.partner_2

        cls.tag = cls.env["forum.tag"].create({"name": "Tag", "forum_id": cls.forum.id})
        cls.tag.follower_ids = cls.partner_3

    @users("Armande")
    def test_post_create_question(self):
        """When creating a question, only the followers of the tags should be notified."""
        with self.mock_mail_gateway():
            self.env["forum.post"].create(
                {"name": "question", "tag_ids": self.tag.ids, "forum_id": self.forum.id}
            )

        self.assertSentEmail(self.env.user.partner_id, self.partner_3)
        self.assertEqual(len(self._new_mails), 1)
        self.assertIn("A new question", self._new_mails.body_html)

    @users("Armande")
    def test_post_create_answer(self):
        """When creating an answer, the followers of the question / tags should be notified."""
        with self.mock_mail_gateway():
            self.env["forum.post"].create(
                {
                    "name": "answer",
                    "tag_ids": self.tag.ids,
                    "forum_id": self.forum.id,
                    "parent_id": self.post.id,
                }
            )

        self.assertSentEmail(self.env.user.partner_id, self.partner_1)
        self.assertSentEmail(self.env.user.partner_id, self.partner_3)
        self.assertEqual(len(self._mails), 2)
        self.assertEqual(len(self._new_mails), 1)
        self.assertIn("A new answer", self._new_mails.body_html)

    @users("Armande")
    def test_post_comment_question(self):
        """When commenting a question, only the followers of the question should be notified."""
        with self.mock_mail_gateway():
            self.env["forum.post.comment"].create(
                {"post_id": self.post.id, "body": "comment body"}
            )._notify_followers()

        self.assertSentEmail(self.env.user.partner_id, self.partner_1)
        self.assertEqual(len(self._new_mails), 1)
        self.assertIn("comment body", self._new_mails.body_html)

    @users("Armande")
    def test_post_comment_answer(self):
        """When commenting an answer, the followers of the answer should be notified."""
        with self.mock_mail_gateway():
            self.env["forum.post.comment"].create(
                {"post_id": self.answer.id, "body": "comment body"}
            )._notify_followers()

        self.assertSentEmail(self.env.user.partner_id, self.partner_2)
        self.assertEqual(len(self._new_mails), 1)
        self.assertIn("comment body", self._new_mails.body_html)

    @users("Armande")
    def test_post_edit_question(self):
        """When editing a question, the followers of the question should be notified."""
        with self.mock_mail_gateway():
            self.post.with_user(self.env.user).content = 'edited'

        self.assertSentEmail(self.env.user.partner_id, self.partner_1)
        self.assertEqual(len(self._new_mails), 1)
        self.assertIn("Question Edited", self._new_mails.body_html)

    @users("Armande")
    def test_post_edit_answer(self):
        """When editing an answer, the followers of the question / answer should be notified."""
        with self.mock_mail_gateway():
            self.answer.with_user(self.env.user).content = 'edited'

        self.assertSentEmail(self.env.user.partner_id, self.partner_1)
        self.assertSentEmail(self.env.user.partner_id, self.partner_2)
        self.assertEqual(len(self._mails), 2)
        self.assertEqual(len(self._new_mails), 1)
        self.assertIn("Answer Edited", self._new_mails.body_html)
