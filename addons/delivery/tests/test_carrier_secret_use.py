from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestCarrierSecretUse(TransactionCase):
    def _carrier_with_secrets(self):
        product = self.env["product.product"].create(
            {"name": "Shipping under test", "type": "service"}
        )
        carrier = self.env["delivery.carrier"].create(
            {"name": "Carrier under test", "product_id": product.id}
        )
        carrier._set_held_secrets({"api_key": "carrier-key"})
        carrier._set_held_secrets({"account_token": "carrier-token"})
        carrier.carrier_credential_id.sudo().write(
            {"decrypt_rate_limit_enabled": True, "decrypt_rate_limit_max": 1}
        )
        return carrier

    def test_rating_reads_the_carrier_secrets_past_the_decrypt_allowance(self):
        carrier = self._carrier_with_secrets()
        public = self.env(user=self.env.ref("base.public_user"))

        for _ in range(3):
            self.env.invalidate_all()
            as_shopper = carrier.with_env(public).sudo()
            self.assertEqual(as_shopper._get_held_secret("api_key"), "carrier-key")
            self.assertEqual(
                as_shopper._get_held_secret("account_token"), "carrier-token"
            )
