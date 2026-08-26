from odoo.tests import TransactionCase, tagged


@tagged("mail_message")
class TestMailMessageSearch(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.message_body_to_search_term = {
            '"hello world"': "&quot;hello world&quot;",
            "it's a test": "it&#x27;s",
            "java`script": "java&#x60;script",
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
        for message, (raw_body, search_term) in zip(
            self.created_messages,
            self.message_body_to_search_term.items(),
        ):
            with self.subTest(search_term=search_term):
                self.assertIn(raw_body, message.body)
                result = self.env["mail.message"]._message_fetch(
                    domain=[],
                    thread=self.channel,
                    search_term=search_term,
                    prettified_search_term=search_term,
                )
                self.assertIn(message, result["messages"])
