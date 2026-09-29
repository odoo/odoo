from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.tests import HttpCase, tagged


@tagged("mail_message")
class TestMailMessageSearch(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.message_body_to_search_term = {
            '"hello world"': '"hello world"',
            "it's a test": "it's",
            "java`script": "java`script",
        }
        cls.channel = cls.env["discuss.channel"].create(
            {
                "name": "Test Search Channel",
                "channel_type": "channel",
            },
        )
        cls.created_messages = [
            cls.channel.message_post(body=body)
            for body in cls.message_body_to_search_term
        ]

    def test_message_search_matches_html_encoded_quotes(self):
        for message, search_term in zip(
            self.created_messages,
            self.message_body_to_search_term.values(),
        ):
            with self.subTest(search_term=search_term):
                result = self.env["mail.message"]._message_fetch(
                    domain=[],
                    thread=self.channel,
                    search_term=search_term,
                )
                self.assertIn(message, result["messages"])

    def test_message_search_include_polls(self):
        """Ensure that poll messages are included in search results when searching
        by poll question or option label, including when searching bookmarked messages.
        """
        user_employee = mail_new_test_user(self.env, "employee", groups="base.group_user")
        self.authenticate(user_employee.login, user_employee.login)
        poll_id = self.make_jsonrpc_request(
            "/mail/poll/create",
            {
                "duration": 10,
                "options": [{"label": "Burger"}, {"label": "Pizza"}],
                "question": "What is your favorite food?",
                "thread_id": self.channel.id,
                "thread_model": self.channel._name,
            },
        )
        poll = self.env["mail.poll"].browse(poll_id)
        self.make_jsonrpc_request(
            "/mail/poll/vote", {"poll_id": poll.id, "option_ids": poll.option_ids[0].ids},
        )
        self.make_jsonrpc_request(
            "/mail/poll/end", {"poll_id": poll.id},
        )
        for search_term, expected_messages in [
            ("Burger", poll.start_message_id | poll.end_message_id),
            ("Pizza", poll.start_message_id),
            ("favorite food", poll.start_message_id | poll.end_message_id),
        ]:
            with self.subTest(search_term=search_term):
                result = self.env["mail.message"].with_user(user_employee)._message_fetch(
                    domain=[],
                    thread=self.channel,
                    search_term=search_term,
                )
                self.assertEqual(result["messages"], expected_messages)
        poll.end_message_id.bookmarked_partner_ids = user_employee.partner_id
        result = self.env["mail.message"].with_user(user_employee)._message_fetch(
            domain=[("bookmarked_partner_ids", "=", user_employee.partner_id.id)],
            search_term="Burger",
        )
        self.assertEqual(result["messages"], poll.end_message_id)
