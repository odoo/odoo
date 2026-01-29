from odoo.tests.common import TransactionCase
from unittest import mock
from datetime import datetime
from freezegun import freeze_time


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

    def test_generate_oauth2_string_token(self):
        """Testing the generation of the oauth2 token
        should take care of google_gmail_mixin.GMAIL_TOKEN_VALIDITY_THRESHOLD
        """
        current_token_expiry = int(datetime(2021, 12, 15, 11, 0, 0).timestamp())
        new_token_expiry = int(datetime(2021, 12, 15, 12, 0, 1).timestamp())
        cases = [
            (
                "2021-12-15 10:59:50",
                False,
                "fake_access_token",
                ("Google Gmail: reuse existing access token. Expire in %i minutes", 0),
            ),
            (
                "2021-12-15 10:59:55",
                True,
                "new-access-token",
                ("Google Gmail: fetch new access token. Expires in %i minutes", 60),
            ),
            (
                "2021-12-15 11:00:01",
                True,
                "new-access-token",
                ("Google Gmail: fetch new access token. Expires in %i minutes", 60),
            ),
        ]

        for (
            current_datetime,
            assert_new_token_generation_called,
            expected_token,
            expected_log,
        ) in cases:
            with self.subTest(currenct_datetime=current_datetime), \
                freeze_time(current_datetime), \
                mock.patch("odoo.addons.google_gmail.models.google_gmail_mixin._logger.info") as mock_logger, \
                mock.patch(
                    "odoo.addons.google_gmail.models.google_gmail_mixin.GoogleGmailMixin._fetch_gmail_access_token",
                    return_value=("new-access-token", new_token_expiry),
                ) as mock_fetch_gmail_access_token:
                self.mail_server.google_gmail_access_token_expiration = current_token_expiry
                oauth2_string = self.mail_server._generate_oauth2_string(
                    "user-account", "refresh-token"
                )
                self.assertEqual(
                    f"user=user-account\1auth=Bearer {expected_token}\1\1",
                    oauth2_string,
                )
                if assert_new_token_generation_called:
                    mock_fetch_gmail_access_token.assert_called_once()
                else:
                    mock_fetch_gmail_access_token.assert_not_called()

                mock_logger.assert_called_once_with(*expected_log)
