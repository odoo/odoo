from unittest.mock import MagicMock, patch

from odoo.libs.guarded_http import GuardedSession
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestGoogleCredentials(TransactionCase):
    """The Google OAuth tokens rest in the vault and the fields are doors.

    They live on `res.users.settings`, which is where the columns were;
    `res.users` reaches them through the related fields it already had.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = cls.env["res.users"].create(
            {"name": "Google User", "login": "google_user_probe"}
        )
        cls.settings = cls.env["res.users.settings"]._get_or_create_for_user(cls.user)

    def test_writing_tokens_creates_one_credential_holding_both(self):
        self.settings._set_google_auth_tokens("an-access", "a-refresh", 3600)

        credential = self.settings.google_calendar_credential_id.sudo()
        self.assertTrue(credential)
        self.assertEqual(credential.oauth_access_token, "an-access")
        self.assertEqual(credential.oauth_refresh_token, "a-refresh")

    def test_the_fields_read_back_what_was_written(self):
        self.settings._set_google_auth_tokens("round-access", "round-refresh", 3600)
        self.settings.invalidate_recordset()

        self.assertEqual(self.settings.google_calendar_token, "round-access")
        self.assertEqual(self.settings.google_calendar_rtoken, "round-refresh")

    def test_the_user_reads_them_through_its_related_fields(self):
        self.settings._set_google_auth_tokens("via-user", "via-user-refresh", 3600)
        self.user.invalidate_recordset()

        self.assertEqual(self.user.google_calendar_token, "via-user")
        self.assertEqual(self.user.google_calendar_rtoken, "via-user-refresh")

    def test_holding_a_token_is_what_authenticated_means(self):
        self.assertFalse(self.settings._google_calendar_authenticated())

        self.settings._set_google_auth_tokens("a", "a-refresh", 3600)

        self.assertTrue(self.settings._google_calendar_authenticated())

    def test_refreshing_the_access_token_leaves_the_refresh_token_alone(self):
        # `_refresh_google_calendar_token` writes the access token and nothing
        # else, which is the case a naive inverse would clear the other half in.
        self.settings._set_google_auth_tokens("first-access", "the-refresh", 3600)

        self.settings.sudo().write({"google_calendar_token": "second-access"})
        self.settings.invalidate_recordset()

        self.assertEqual(self.settings.google_calendar_token, "second-access")
        self.assertEqual(
            self.settings.google_calendar_rtoken,
            "the-refresh",
            "a token refresh must not discard the token it refreshed with",
        )

    def test_disconnecting_unlinks_the_credential(self):
        self.settings._set_google_auth_tokens("gone", "gone-refresh", 3600)
        credential = self.settings.google_calendar_credential_id

        self.settings._set_google_auth_tokens(False, False, 0)

        self.assertFalse(self.settings.google_calendar_credential_id)
        self.assertFalse(credential.exists())
        self.assertFalse(self.settings._google_calendar_authenticated())

    def test_the_tokens_are_still_kept_out_of_session_info(self):
        blacklist = self.env["res.users.settings"]._get_fields_blacklist()

        self.assertIn("google_calendar_rtoken", blacklist)
        self.assertIn("google_calendar_token", blacklist)

    def test_no_plaintext_column_survives(self):
        self.env.cr.execute(
            """
            SELECT column_name FROM information_schema.columns
             WHERE table_name = 'res_users_settings'
               AND column_name IN ('google_calendar_token', 'google_calendar_rtoken')
            """
        )
        self.assertEqual(
            self.env.cr.fetchall(),
            [],
            "the migration drops the columns; a nulled one still sits in every "
            "backup taken before it was nulled",
        )

    def test_an_expired_token_is_refreshed_and_the_new_one_is_returned(self):
        self.settings._set_google_auth_tokens("stale-access", "the-refresh", 0)
        response = MagicMock(ok=True)
        response.json.return_value = {
            "access_token": "fresh-access",
            "expires_in": 3600,
        }

        with patch.object(GuardedSession, "request", return_value=response) as sent:
            token = self.user._get_google_calendar_token()

        self.assertEqual(token, "fresh-access")
        self.assertEqual(sent.call_args.kwargs["data"]["refresh_token"], "the-refresh")
        self.assertTrue(self.settings._is_google_calendar_valid())
        self.assertEqual(self.settings.google_calendar_rtoken, "the-refresh")


@tagged("post_install", "-at_install")
class TestCalendarProviderWizardCredentials(TransactionCase):
    def test_the_setup_wizard_stores_the_client_secret_where_google_reads_it(self):
        wizard = self.env["calendar.provider.config"].create(
            {
                "external_calendar_provider": "google",
                "cal_client_id": "wizard-client",
                "cal_client_secret": "wizard-secret",
            }
        )

        wizard.action_calendar_prepare_external_provider_sync()

        Credential = self.env["credential.credential"]
        self.assertEqual(
            Credential._get_system_secret("google_calendar_client_secret"),
            "wizard-secret",
        )
        self.assertFalse(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("google_calendar_client_secret")
        )
        self.assertEqual(
            self.env["calendar.provider.config"].default_get(["cal_client_secret"])[
                "cal_client_secret"
            ],
            "wizard-secret",
        )
