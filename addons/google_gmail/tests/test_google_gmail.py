from datetime import datetime
from unittest import mock

from freezegun import freeze_time

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestIrMailServer(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.mail_server = cls.env["ir.mail_server"].create(
            {
                "name": "Gmail",
                "smtp_host": "fake.host",
                "google_gmail_access_token": "fake_access_token",
            }
        )

    def test_gmail_server_defaults_to_verified_starttls(self):
        server = self.env["ir.mail_server"].new({"smtp_authentication": "gmail"})
        server._onchange_smtp_authentication_gmail()
        self.assertEqual(server.smtp_encryption, "starttls_strict")
        for encryption in ("starttls_strict", "starttls"):
            self.env["ir.mail_server"].create(
                {
                    "name": f"gmail-{encryption}",
                    "smtp_host": "smtp.gmail.com",
                    "smtp_authentication": "gmail",
                    "smtp_user": "me@gmail.com",
                    "smtp_encryption": encryption,
                }
            )
        with self.assertRaises(UserError):
            self.env["ir.mail_server"].create(
                {
                    "name": "gmail-ssl",
                    "smtp_host": "smtp.gmail.com",
                    "smtp_authentication": "gmail",
                    "smtp_user": "me@gmail.com",
                    "smtp_encryption": "ssl_strict",
                }
            )

    def test_generate_oauth2_string_token(self):
        """Testing the generation of the oauth2 token
        should take care of OAUTH2_TOKEN_VALIDITY_THRESHOLD
        """
        current_token_expiry = int(datetime(2021, 12, 15, 11, 0, 0).timestamp())
        new_token_expiry = int(datetime(2021, 12, 15, 12, 0, 1).timestamp())
        cases = [
            (
                "2021-12-15 10:59:50",
                False,
                "fake_access_token",
                (
                    "%s: reuse existing access token. It expires in %i minutes",
                    "Gmail",
                    0,
                ),
            ),
            (
                "2021-12-15 10:59:55",
                True,
                "new-access-token",
                ("%s: fetch new access token. It expires in %i minutes", "Gmail", 60),
            ),
            (
                "2021-12-15 11:00:01",
                True,
                "new-access-token",
                ("%s: fetch new access token. It expires in %i minutes", "Gmail", 60),
            ),
        ]

        for (
            current_datetime,
            assert_new_token_generation_called,
            expected_token,
            expected_log,
        ) in cases:
            with (
                self.subTest(currenct_datetime=current_datetime),
                freeze_time(current_datetime),
                mock.patch(
                    "odoo.addons.mail_oauth2.models.mixin_oauth2_mail_provider._logger.info"
                ) as mock_logger,
                mock.patch(
                    "odoo.addons.google_gmail.models.mixin_google_gmail.MixinGoogleGmail._get_gmail_access_token_iap",
                    return_value=("new-access-token", new_token_expiry),
                ) as mock_get_gmail_access_token,
            ):
                self.mail_server.google_gmail_access_token_expiration = (
                    current_token_expiry
                )
                oauth2_string = self.mail_server._generate_oauth2_string(
                    "user-account", "refresh-token"
                )
                self.assertEqual(
                    f"user=user-account\1auth=Bearer {expected_token}\1\1",
                    oauth2_string,
                )
                if assert_new_token_generation_called:
                    mock_get_gmail_access_token.assert_called_once()
                else:
                    mock_get_gmail_access_token.assert_not_called()

                mock_logger.assert_called_once_with(*expected_log)
