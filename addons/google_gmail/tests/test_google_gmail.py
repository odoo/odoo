# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import TransactionCase


class TestGoogleGmail(TransactionCase):
    def test_google_gmail_token(self):
        GmailToken = self.env["google.gmail.token"]

        token = GmailToken._search_or_create("existing_user@example.com", {"google_gmail_refresh_token": "token 1"})
        unused_token = GmailToken._search_or_create("unused_token@example.com", {"google_gmail_refresh_token": "token 2"})

        servers = self.env["ir.mail_server"].create([
            self._get_ir_mail_server_values('"Alice" <user_1@example.com>'),
            self._get_ir_mail_server_values('"Eve" <existing_user@example.com>'),
            self._get_ir_mail_server_values('"Bob" <user_1@example.com>'),
            self._get_ir_mail_server_values('user_2@example.com'),
        ])
        for server in servers:
            GmailToken._search_or_create(server.smtp_user, {"google_gmail_refresh_token": "token"})

        tokens = [server.google_gmail_token_id.id for server in servers]

        self.assertEqual(len(tokens), 4)
        self.assertEqual(len(set(tokens)), 3)
        self.assertEqual(token.id, tokens[1], "Should reuse the existing token")
        self.assertEqual(tokens[0], tokens[2], "Should share the same token")

        incoming_servers = self.env["fetchmail.server"].create([
            self._get_fetchmail_server_values("user_1@example.com"),
            self._get_fetchmail_server_values("user_3@example.com"),
        ])
        for server in incoming_servers:
            GmailToken._search_or_create(server.user, {"google_gmail_refresh_token": "token"})

        incoming_tokens = [server.google_gmail_token_id.id for server in incoming_servers]
        self.assertEqual(len(set(incoming_tokens)), 2)
        self.assertEqual(incoming_tokens[0], tokens[0], "Should share the same token")

        self.assertTrue(unused_token.exists())

        self.assertEqual(GmailToken.search_count([]), 5)
        GmailToken._gc_google_gmail_token()
        self.assertFalse(unused_token.exists(), "Should have removed the unused token")
        self.assertEqual(GmailToken.search_count([]), 4, "Should have kept all other tokens")

    def _get_ir_mail_server_values(self, email):
        return {
            "name": email,
            "from_filter": email,
            "smtp_authentication": "gmail",
            "smtp_encryption": "starttls",
            "smtp_host": "host",
            "smtp_user": email,
        }

    def _get_fetchmail_server_values(self, email):
        return {
            "name": email,
            "server": "host",
            "server_type": "gmail",
            "user": email,
        }
