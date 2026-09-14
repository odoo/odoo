import unittest
from urllib.parse import parse_qs, urlsplit

from odoo.tests import TransactionCase, tagged


PROVIDER_MIXINS = ("mixin.google.gmail", "mixin.microsoft.outlook")


@tagged("post_install", "-at_install")
class TestProviderIsolation(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if any(name not in cls.env.registry for name in PROVIDER_MIXINS):
            raise unittest.SkipTest("needs both bundled providers installed")

        Config = cls.env["ir.config_parameter"].sudo()
        Config.set_param("google_gmail_client_id", "GOOGLE-ID")
        Vault = cls.env["credential.credential"]
        Vault._set_system_secret("google_gmail_client_secret", "GOOGLE-SECRET")
        Config.set_param("microsoft_outlook_client_id", "MICROSOFT-ID")
        Vault._set_system_secret("microsoft_outlook_client_secret", "MICROSOFT-SECRET")

        cls.server = cls.env["ir.mail_server"].create(
            {
                "name": "Two providers",
                "smtp_host": "smtp.example.com",
                "smtp_user": "user@example.com",
            }
        )
        cls.server.invalidate_recordset()

    def _params(self, uri):
        return {key: values[0] for key, values in parse_qs(urlsplit(uri).query).items()}

    def test_each_provider_keeps_its_own_credentials(self):
        gmail = self._params(self.server.google_gmail_uri)
        outlook = self._params(self.server.microsoft_outlook_uri)

        self.assertEqual(gmail["client_id"], "GOOGLE-ID")
        self.assertEqual(outlook["client_id"], "MICROSOFT-ID")

    def test_each_provider_keeps_its_own_endpoint_and_route(self):
        self.assertTrue(
            self.server.google_gmail_uri.startswith("https://accounts.google.com/")
        )
        self.assertIn("login.microsoftonline.com", self.server.microsoft_outlook_uri)

        gmail = self._params(self.server.google_gmail_uri)
        outlook = self._params(self.server.microsoft_outlook_uri)
        self.assertTrue(gmail["redirect_uri"].endswith("/google_gmail/confirm"))
        self.assertTrue(outlook["redirect_uri"].endswith("/microsoft_outlook/confirm"))

    def test_each_provider_keeps_its_own_scope_and_extra_params(self):
        gmail = self._params(self.server.google_gmail_uri)
        outlook = self._params(self.server.microsoft_outlook_uri)

        self.assertIn("https://mail.google.com/", gmail["scope"])
        self.assertIn("offline_access", outlook["scope"])
        self.assertIn(self.server._OUTLOOK_SCOPE, outlook["scope"])

        self.assertEqual(gmail["access_type"], "offline")
        self.assertNotIn("response_mode", gmail)
        self.assertEqual(outlook["response_mode"], "query")
        self.assertNotIn("access_type", outlook)

    def test_csrf_tokens_are_scoped_per_provider(self):
        self.assertNotEqual(
            self.server._get_gmail_csrf_token(),
            self.server._get_outlook_csrf_token(),
        )

    def test_unsaved_record_carries_no_id(self):
        draft = self.env["ir.mail_server"].new({"name": "draft"})
        for uri in (draft.google_gmail_uri, draft.microsoft_outlook_uri):
            self.assertEqual(self._params(uri)["state"].count("false"), 2)
