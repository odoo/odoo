from odoo.tests import TransactionCase, tagged


@tagged("mail_message", "-at_install")
class TestMailMessageSearch(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.message_body_to_search_term = {
            '<p>"hello world"</p>': "&quot;hello world&quot;",
            "<p>it's a test</p>": "it&#x27;s",
            "<p>java`script</p>": "java&#x60;script",
            "<p>&lt;hii&gt;</p>": "&lt;hii&gt;",
        }
        cls.channel = cls.env["discuss.channel"].create(
            {
                "name": "Test Search Channel",
                "channel_type": "channel",
            },
        )
        cls.MailMessage = cls.env["mail.message"]
        cls.created_messages = cls.MailMessage.create(
            [
                {
                    "model": "discuss.channel",
                    "res_id": cls.channel.id,
                    "message_type": "comment",
                    "body": body,
                }
                for body in cls.message_body_to_search_term
            ],
        )

    def test_message_search_matches_html_encoded_quotes(self):
        for message, search_term in zip(
            self.created_messages, self.message_body_to_search_term.values(),
        ):
            with self.subTest(search_term=search_term):
                result = self.MailMessage._message_fetch(
                    domain=[],
                    thread=self.channel,
                    search_term=search_term,
                )
                self.assertIn(message, result["messages"])
