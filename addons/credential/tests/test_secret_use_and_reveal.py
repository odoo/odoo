from unittest.mock import patch

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestSecretUseAndReveal(TransactionCase):
    def _credential(self, **payload):
        return self.env["credential.credential"].create(
            {
                "name": "use vs reveal",
                "category_id": self.env.ref(
                    "credential.credential_category_api_key"
                ).id,
                "decrypt_rate_limit_enabled": True,
                "decrypt_rate_limit_max": 1,
                **payload,
            }
        )

    def _read_rows(self, credential):
        return self.env["credential.access.log"].search_count(
            [("credential_id", "=", credential.id), ("operation", "=", "read")]
        )

    def test_use_neither_spends_the_allowance_nor_writes_a_read_row(self):
        credential = self._credential(api_key="K")

        for _ in range(3):
            self.env.invalidate_all()
            self.assertEqual(credential._use_secret("test:use", prefer="api_key"), "K")

        self.assertEqual(self._read_rows(credential), 0)

    def test_use_basic_auth_reads_the_pair_without_the_allowance(self):
        credential = self.env["credential.credential"].create(
            {
                "name": "pair",
                "category_id": self.env.ref(
                    "credential.credential_category_basic_auth"
                ).id,
                "decrypt_rate_limit_enabled": True,
                "decrypt_rate_limit_max": 1,
                "username": "u",
                "password": "p",
            }
        )

        for _ in range(3):
            self.env.invalidate_all()
            self.assertEqual(credential._use_basic_auth("test:use"), ("u", "p"))

    def test_a_rolled_back_reveal_is_still_audited(self):
        credential = self._credential(api_key="K")
        self.env.invalidate_all()
        store = type(credential)

        with patch.object(store, "_log_access_out_of_band") as out_of_band:
            self.assertEqual(credential.api_key, "K")
            self.env.cr.postrollback.run()

        out_of_band.assert_called_once_with("read")
