from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestMicrosoftCredentials(TransactionCase):
    """The Microsoft OAuth tokens rest in the vault and the fields are doors.

    `microsoft_calendar_token_validity` is not among them: an expiry is not a
    secret, and it stays a column on the user.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = cls.env["res.users"].create(
            {"name": "Outlook User", "login": "outlook_user_probe"}
        )

    def test_writing_tokens_creates_one_credential_holding_both(self):
        self.user._set_microsoft_auth_tokens("an-access", "a-refresh", 3600)

        credential = self.user.microsoft_calendar_credential_id.sudo()
        self.assertTrue(credential)
        self.assertEqual(credential.oauth_access_token, "an-access")
        self.assertEqual(credential.oauth_refresh_token, "a-refresh")

    def test_the_fields_read_back_what_was_written(self):
        self.user._set_microsoft_auth_tokens("round-access", "round-refresh", 3600)
        self.user.invalidate_recordset()

        self.assertEqual(self.user.microsoft_calendar_token, "round-access")
        self.assertEqual(self.user.microsoft_calendar_rtoken, "round-refresh")

    def test_a_refresh_alone_is_enough_to_hold_a_credential(self):
        # The steady state: the access token has expired and been discarded, and
        # the refresh token is what buys the next one.
        self.user._microsoft_store_tokens(refresh_token="only-a-refresh")

        self.assertTrue(self.user.microsoft_calendar_credential_id)
        self.assertEqual(self.user.microsoft_calendar_rtoken, "only-a-refresh")

    def test_refreshing_the_access_token_leaves_the_refresh_token_alone(self):
        self.user._set_microsoft_auth_tokens("first-access", "the-refresh", 3600)

        self.user._microsoft_store_tokens(access_token="second-access")
        self.user.invalidate_recordset()

        self.assertEqual(self.user.microsoft_calendar_token, "second-access")
        self.assertEqual(
            self.user.microsoft_calendar_rtoken,
            "the-refresh",
            "a token refresh must not discard the token it refreshed with",
        )

    def test_clearing_both_unlinks_the_credential(self):
        self.user._set_microsoft_auth_tokens("gone-access", "gone-refresh", 3600)
        credential = self.user.microsoft_calendar_credential_id

        self.user._set_microsoft_auth_tokens(False, False, 0)

        self.assertFalse(self.user.microsoft_calendar_credential_id)
        self.assertFalse(credential.exists())

    def test_a_user_who_never_connected_reads_empty(self):
        self.assertFalse(self.user.microsoft_calendar_credential_id)
        self.assertFalse(self.user.microsoft_calendar_token)
        self.assertFalse(self.user.microsoft_calendar_rtoken)

    def test_no_plaintext_column_survives(self):
        self.env.cr.execute(
            """
            SELECT column_name FROM information_schema.columns
             WHERE table_name = 'res_users'
               AND column_name IN ('microsoft_calendar_token',
                                   'microsoft_calendar_rtoken')
            """
        )
        self.assertEqual(
            self.env.cr.fetchall(),
            [],
            "the migration drops the columns; a nulled one still sits in every "
            "backup taken before it was nulled",
        )

    def test_the_expiry_is_not_a_secret_and_stays_a_column(self):
        self.assertTrue(
            self.env["res.users"]._fields["microsoft_calendar_token_validity"].store
        )
