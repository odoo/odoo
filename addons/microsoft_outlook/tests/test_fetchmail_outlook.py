import time
from unittest.mock import ANY, Mock, patch

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestFetchmailOutlook(TransactionCase):
    @patch("odoo.addons.mail.tools.incoming_mail.OdooIMAP4_SSL")
    def test_connect(self, mock_imap):
        """Test that the connect method will use the right
        authentication method with the right arguments.
        """
        mock_connection = Mock()
        mock_imap.return_value = mock_connection

        mail_server = self.env["fetchmail.server"].create(
            {
                "name": "Test server",
                "server_type": "outlook",
                "user": "test@example.com",
                "microsoft_outlook_access_token": "test_access_token",
                "microsoft_outlook_access_token_expiration": time.time() + 1000000,
                "password": "",
                "encryption": "ssl_strict",
            }
        )

        mail_server._connect__()

        mock_connection.authenticate.assert_called_once_with("XOAUTH2", ANY)
        args = mock_connection.authenticate.call_args[0]

        self.assertEqual(
            args[1](None),
            "user=test@example.com\1auth=Bearer test_access_token\1\1",
            msg="Should use the right access token",
        )

        mock_connection.select.assert_not_called()

    def test_outgoing_server_defaults_to_verified_starttls(self):
        server = self.env["ir.mail_server"].new({"smtp_authentication": "outlook"})
        server._onchange_smtp_authentication_outlook()
        self.assertEqual(server.smtp_encryption, "starttls_strict")
        for encryption in ("starttls_strict", "starttls"):
            self.env["ir.mail_server"].create(
                {
                    "name": f"outlook-{encryption}",
                    "smtp_host": "smtp.outlook.com",
                    "smtp_authentication": "outlook",
                    "smtp_user": "me@outlook.com",
                    "smtp_encryption": encryption,
                }
            )
        with self.assertRaises(UserError):
            self.env["ir.mail_server"].create(
                {
                    "name": "outlook-ssl",
                    "smtp_host": "smtp.outlook.com",
                    "smtp_authentication": "outlook",
                    "smtp_user": "me@outlook.com",
                    "smtp_encryption": "ssl_strict",
                }
            )

    def test_constraints(self):
        """Test the constraints related to the Outlook mail server."""
        with self.assertRaises(
            UserError, msg="Should ensure that the password is empty"
        ):
            self.env["fetchmail.server"].create(
                {
                    "name": "Test server",
                    "server_type": "outlook",
                    "password": "test",
                }
            )
