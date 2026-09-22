from odoo.tests import tagged

from .common import DeviceTransactionCase


@tagged("post_install", "-at_install")
class TestRemoteConfigSecretsLiveInTheVault(DeviceTransactionCase):
    def _columns(self):
        self.env.cr.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'device_profile' AND column_name IN "
            "('auth_password', 'auth_token')"
        )
        return {row[0] for row in self.env.cr.fetchall()}

    def test_the_device_secrets_are_not_columns_of_the_profile(self):
        self.assertEqual(self._columns(), set())

    def test_a_token_profile_keeps_its_token_in_an_encrypted_credential(self):
        config = self._create_device_profile(
            name="Vault token profile", auth_type="bearer", auth_token="dev-token"
        )

        self.assertEqual(config.auth_token, "dev-token")
        credential = config.sudo().credential_id
        self.assertTrue(credential)
        self.assertTrue(credential.credential_value_encrypted)

    def test_polling_reads_the_secret_past_the_decrypt_allowance(self):
        config = self._create_device_profile(
            name="Vault basic profile",
            auth_type="basic",
            auth_username="device",
            auth_password="device-pass",
        )
        config.sudo().credential_id.write(
            {"decrypt_rate_limit_enabled": True, "decrypt_rate_limit_max": 1}
        )

        for _ in range(3):
            self.env.invalidate_all()
            self.assertEqual(config.sudo().auth_password, "device-pass")

    def test_clearing_the_token_clears_it_in_the_vault(self):
        config = self._create_device_profile(
            name="Vault cleared profile", auth_type="bearer", auth_token="dev-token"
        )

        config.auth_token = False
        self.env.invalidate_all()

        self.assertFalse(config.auth_token)
