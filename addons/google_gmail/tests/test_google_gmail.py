from odoo.tests.common import TransactionCase
from unittest import mock
from datetime import datetime
from freezegun import freeze_time


class TestIrMailServer(TransactionCase):

    @freeze_time("2021-12-15 10:59:50")
    def test_generate_oauth2_string_token_valid(self):
        """Check that existing token expire in more than
        GMAIL_TOKEN_VALIDITY_THRESHOLD seconds existing token is used.
        """
        mail_server = self.env["ir.mail_server"].new(
            {
                "google_gmail_access_token": "fake_access_token",
                "google_gmail_access_token_expiration": int(datetime(2021, 12, 15, 11, 0, 0).timestamp()),
            }
        )
        oauth2_string = mail_server._generate_oauth2_string("user-account", "refresh-token")
        self.assertIn("fake_access_token", oauth2_string)

    @freeze_time("2021-12-15 10:59:55")
    def test_generate_oauth2_string_token_expire_in_less_than_GMAIL_TOKEN_VALIDITY_THRESHOLDs(self):
        """Check that existing token expire in less than
        GMAIL_TOKEN_VALIDITY_THRESHOLD seconds a new token is generated.
        """
        mail_server = self.env["ir.mail_server"].new(
            {
                "google_gmail_access_token": "fake_access_token",
                "google_gmail_access_token_expiration": int(datetime(2021, 12, 15, 11, 0, 0).timestamp()),
            }
        )
        with mock.patch(
            "odoo.addons.google_gmail.models.google_gmail_mixin.GoogleGmailMixin._fetch_gmail_access_token",
            return_value=("new-access-token", int(datetime(2021, 12, 15, 12, 0, 0).timestamp()))
        ):
            oauth2_string = mail_server._generate_oauth2_string("user-account", "refresh-token")
        self.assertIn("new-access-token", oauth2_string)

    @freeze_time("2021-12-15 11:00:01")
    def test_generate_oauth2_string_token_expired(self):
        """Check that existing token is already expired
        a new token is generated.
        """
        mail_server = self.env["ir.mail_server"].new(
            {
                "google_gmail_access_token": "fake_access_token",
                "google_gmail_access_token_expiration": int(datetime(2021, 12, 15, 11, 0, 0).timestamp()),
            }
        )
        with mock.patch(
            "odoo.addons.google_gmail.models.google_gmail_mixin.GoogleGmailMixin._fetch_gmail_access_token",
            return_value=("new-access-token", int(datetime(2021, 12, 15, 12, 0, 1).timestamp()))
        ):
            oauth2_string = mail_server._generate_oauth2_string("user-account", "refresh-token")
        self.assertIn("new-access-token", oauth2_string)
