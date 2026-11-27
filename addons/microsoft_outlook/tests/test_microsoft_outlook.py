from odoo.tests.common import TransactionCase
from unittest import mock


class TestIrMailServer(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.mail_server = cls.env["ir.mail_server"].create(
            {
                "name": "Outlook",
                "smtp_host": "smtp.outlook.com",
                "smtp_authentication": "outlook",
                "smtp_user": "test@example.com",
                "smtp_encryption": "starttls",
                "from_filter": "test@example.com",
            }
        )

    def test_redirect_uri_ignores_context_website(self):
        """The redirect URI must match the one registered on the Microsoft side,
        whatever the website in context (e.g. sending a mail during a website request).
        """
        def get_base_url(record):
            # mimic `website`, whose `get_base_url` follows the website in context
            if record.env.context.get('website_id'):
                return 'https://website.example.com'
            return 'https://db.example.com'

        self.env['ir.config_parameter'].sudo().set_param('microsoft_outlook_client_id', 'test_client_id')
        self.env['ir.config_parameter'].sudo().set_param('microsoft_outlook_client_secret', 'test_client_secret')
        expected_redirect_uri = 'https://db.example.com/microsoft_outlook/confirm'
        mail_server = self.mail_server.with_context(website_id=1)

        with mock.patch.object(type(self.mail_server), 'get_base_url', get_base_url), \
             mock.patch('odoo.addons.microsoft_outlook.models.microsoft_outlook_mixin.requests.post',
                        return_value=mock.Mock(ok=True, json=dict)) as mock_post:
            mail_server._fetch_outlook_token('refresh_token', refresh_token='test_refresh_token')
            self.assertEqual(mock_post.call_args.kwargs['data']['redirect_uri'], expected_redirect_uri)
