from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestCategoryDefaultsOnCreate(TransactionCase):
    def test_a_credential_created_in_code_takes_its_category_policy(self):
        credential = self.env["credential.credential"].create(
            {
                "name": "OAuth2 from code",
                "category_id": self.env.ref("credential.credential_category_oauth2").id,
                "oauth_client_secret": "s",
            }
        )

        self.assertEqual(credential.decrypt_rate_limit_max, 200)

    def test_an_explicit_policy_value_wins_over_the_category(self):
        credential = self.env["credential.credential"].create(
            {
                "name": "OAuth2 with its own cap",
                "category_id": self.env.ref("credential.credential_category_oauth2").id,
                "oauth_client_secret": "s",
                "decrypt_rate_limit_max": 7,
            }
        )

        self.assertEqual(credential.decrypt_rate_limit_max, 7)
