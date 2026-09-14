from odoo.tests import TransactionCase, tagged


SYNC_DOMAIN = [
    ("google_calendar_rtoken", "!=", False),
    ("google_synchronization_stopped", "=", False),
]


@tagged("post_install", "-at_install")
class TestGoogleSyncCandidates(TransactionCase):
    """Who the synchronisation cron picks up, and why it cannot ask SQL.

    This fork keeps the OAuth tokens in `credential.credential`'s encrypted
    JSON, so every field along the way is computed: the credential's
    `oauth_refresh_token`, the settings' `google_calendar_rtoken` onto it, and
    the user's related through `res_users_settings_id`, which has no column of
    its own. The cron used to `search` res.users on that chain and died with
    `Cannot convert res.users.res_users_settings_id to SQL because it is not
    stored` -- on every run, twice a day, even with nobody connected.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = cls.env["res.users"].create(
            {"name": "Sync Candidate", "login": "google_sync_candidate"}
        )
        cls.settings = cls.env["res.users.settings"]._get_or_create_for_user(cls.user)

    def _candidates(self):
        return self.env["res.users"]._google_sync_candidates()

    def test_the_cron_runs_when_nobody_has_connected(self):
        """The failure needed no data at all -- the search itself raised."""
        self.assertNotIn(self.user, self._candidates())

        self.env["res.users"]._sync_all_google_calendar()

    def test_a_connected_user_is_picked_up(self):
        self.settings._set_google_auth_tokens("an-access", "a-refresh", 3600)

        self.assertIn(self.user, self._candidates())

    def test_a_user_who_stopped_syncing_is_left_out(self):
        self.settings._set_google_auth_tokens("an-access", "a-refresh", 3600)
        self.settings.google_synchronization_stopped = True

        self.assertNotIn(self.user, self._candidates())

    def test_a_user_who_never_connected_is_left_out(self):
        self.assertFalse(self.settings.google_calendar_credential_id)

        self.assertNotIn(self.user, self._candidates())

    def test_a_credential_without_a_refresh_token_falls_out_in_python(self):
        """The SQL half is deliberately a superset.

        It can see that a credential is linked but not what is inside it, so
        the token itself is settled by the same domain the cron applies.
        """
        self.settings._set_google_auth_tokens("access-only", False, 3600)
        candidates = self._candidates()

        self.assertIn(
            self.user, candidates, "The link to the credential is stored and matches."
        )
        self.assertNotIn(
            self.user,
            candidates.filtered_domain(SYNC_DOMAIN),
            "There is no refresh token in it, so there is nothing to refresh.",
        )
