from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestDiscussMessageSearch(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.channel = cls.env["discuss.channel"].create(
            {
                "name": "Test Search Channel",
                "channel_type": "channel",
            }
        )
        cls.MailMessage = cls.env["mail.message"]

        cls.msg_double_quote = cls.MailMessage.create(
            {
                "model": "discuss.channel",
                "res_id": cls.channel.id,
                "message_type": "comment",
                "body": '<p>"hello world"</p>',
            }
        )
        cls.msg_single_quote = cls.MailMessage.create(
            {
                "model": "discuss.channel",
                "res_id": cls.channel.id,
                "message_type": "comment",
                "body": "<p>it's a test</p>",
            }
        )
        cls.msg_backtick = cls.MailMessage.create(
            {
                "model": "discuss.channel",
                "res_id": cls.channel.id,
                "message_type": "comment",
                "body": "<p>java`script</p>",
            }
        )
        cls.msg_lt_gt = cls.MailMessage.create(
            {
                "model": "discuss.channel",
                "res_id": cls.channel.id,
                "message_type": "comment",
                "body": "<p>&lt;hii&gt;</p>",
            }
        )
        cls.msg_plain = cls.MailMessage.create(
            {
                "model": "discuss.channel",
                "res_id": cls.channel.id,
                "message_type": "comment",
                "body": "<p>plain text only</p>",
            }
        )

    def _search(self, search_term):
        result = self.MailMessage._message_fetch(
            domain=[],
            thread=self.channel,
            search_term=search_term,
        )
        return result["messages"]

    def test_double_quote_encoded_finds_message(self):
        self.assertIn(
            self.msg_double_quote,
            self._search("&quot;hello world&quot;"),
        )

    def test_single_quote_encoded_finds_message(self):
        self.assertIn(
            self.msg_single_quote,
            self._search("it&#x27;s"),
        )

    def test_backtick_encoded_finds_message(self):
        self.assertIn(
            self.msg_backtick,
            self._search("java&#x60;script"),
        )

    def test_plain_text_unaffected(self):
        self.assertIn(
            self.msg_plain,
            self._search("plain text only"),
        )
