from odoo.tests.common import SavepointCase
from unittest import mock
import time

class TestIrMailServer(SavepointCase):

    def test_generate_oauth2_string_token_valid(self):
        now_timestamp = int(time.time())
        mail_server = self.env["ir.mail_server"].new(
            {
                "google_gmail_access_token": "fake_access_token",
                "google_gmail_access_token_expiration": now_timestamp + 10,
            }
        )
        oauth2_string = mail_server._generate_oauth2_string("user-account", "refresh-token")
        
        self.assertIn("fake_access_token", oauth2_string)


    def test_generate_oauth2_string_token_expire_in_less_than_5s(self):
        now_timestamp = int(time.time())
        mail_server = self.env["ir.mail_server"].new(
            {
                "google_gmail_access_token": "fake_access_token",
                "google_gmail_access_token_expiration": now_timestamp + 2,
            }
        )
        with mock.patch(
            "odoo.addons.google_gmail.models.google_gmail_mixin.GoogleGmailMixin._fetch_gmail_access_token",
            return_value=("new-access-token", now_timestamp + 60*60)
        ):
            oauth2_string = mail_server._generate_oauth2_string("user-account", "refresh-token")
        
        self.assertIn("new-access-token", oauth2_string)

    def test_generate_oauth2_string_token_expired(self):
        now_timestamp = int(time.time())
        mail_server = self.env["ir.mail_server"].new(
            {
                "google_gmail_access_token": "fake_access_token",
                "google_gmail_access_token_expiration": now_timestamp - 2,
            }
        )
        with mock.patch(
            "odoo.addons.google_gmail.models.google_gmail_mixin.GoogleGmailMixin._fetch_gmail_access_token",
            return_value=("new-access-token", now_timestamp + 60*60)
        ):
            oauth2_string = mail_server._generate_oauth2_string("user-account", "refresh-token")
        
        self.assertIn("new-access-token", oauth2_string)