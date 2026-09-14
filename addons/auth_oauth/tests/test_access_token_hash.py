from odoo.exceptions import AccessDenied
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestAccessTokenHash(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = new_test_user(cls.env, "oauth_probe")
        cls.provider = cls.env["auth.oauth.provider"].search([], limit=1)
        cls.user.write({"oauth_provider_id": cls.provider.id, "oauth_uid": "probe-uid"})
        cls.env["res.users"]._auth_oauth_signin(
            cls.provider.id, {"user_id": "probe-uid"}, {"access_token": "tok-1"}
        )

    def _check(self, token):
        return self.user.with_user(self.user)._check_credentials(
            {"type": "oauth_token", "token": token}, {"interactive": True}
        )

    def test_the_token_is_stored_hashed(self):
        self.env.cr.execute(
            "SELECT oauth_access_token_hash FROM res_users WHERE id = %s",
            [self.user.id],
        )
        stored = self.env.cr.fetchone()[0]
        self.assertTrue(stored)
        self.assertNotIn("tok-1", stored)

    def test_the_signed_in_token_authenticates_and_another_does_not(self):
        self.assertEqual(self._check("tok-1")["auth_method"], "oauth")
        with self.assertRaises(AccessDenied):
            self._check("tok-2")

    def test_removing_the_token_stops_it_authenticating(self):
        self.user.sudo().remove_oauth_access_token()
        with self.assertRaises(AccessDenied):
            self._check("tok-1")
