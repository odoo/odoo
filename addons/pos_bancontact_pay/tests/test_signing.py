import json
from types import SimpleNamespace

from odoo.exceptions import UserError
from odoo.tests.common import tagged

from odoo.addons.pos_bancontact_pay import const
from odoo.addons.pos_bancontact_pay.controllers.signature import (
    BancontactSignatureValidation,
)
from odoo.addons.pos_bancontact_pay.tests.common import TestBancontactPay


@tagged("post_install", "-at_install")
class TestSigning(TestBancontactPay):
    _test_user_groups = None  # FIXME list needed groups

    # --------------------------
    # Signing key
    # --------------------------
    def test_signing_key_generated_with_merchant_id(self):
        self.assertFalse(self.company.bancontact_signing_kid)

        self.company.bancontact_merchant_id = "merchant_id"
        kid = self.company.bancontact_signing_kid
        self.assertTrue(kid)
        self.assertTrue(self.company.sudo().bancontact_signing_key)

        # Changing the Merchant ID keeps the key
        self.company.bancontact_merchant_id = "other_merchant_id"
        self.assertEqual(self.company.bancontact_signing_kid, kid)

    def test_regenerate_signing_key(self):
        self.company.bancontact_merchant_id = "merchant_id"
        kid = self.company.bancontact_signing_kid
        jwk = self.company._bancontact_get_public_jwk()

        self.env["res.config.settings"].with_company(self.company).create({}).action_bancontact_regenerate_signing_key()

        self.assertNotEqual(self.company.bancontact_signing_kid, kid)
        new_jwk = self.company._bancontact_get_public_jwk()
        self.assertNotEqual((new_jwk["x"], new_jwk["y"]), (jwk["x"], jwk["y"]))

    # --------------------------
    # JWKS
    # --------------------------
    def test_jwks(self):
        self.company.bancontact_merchant_id = "merchant_id"
        self.company_2.bancontact_merchant_id = "merchant_id_2"
        self.env.flush_all()

        response = self.url_open("/bancontact_pay/jwks")

        self.assertEqual(response.status_code, 200)
        keys = {key["kid"]: key for key in response.json()["keys"]}
        self.assertEqual(keys[self.company.bancontact_signing_kid], self.company._bancontact_get_public_jwk())
        self.assertEqual(keys[self.company_2.bancontact_signing_kid], self.company_2._bancontact_get_public_jwk())
        self.assertEqual(keys[self.company.bancontact_signing_kid]["alg"], "ES256")

    # --------------------------
    # Request signing
    # --------------------------
    def test_sign_bancontact_request(self):
        self.company.bancontact_merchant_id = "merchant_id"
        url = "https://merchant.api.preprod.bancontact.net/v3/payments/payment_id/refunds"
        body = json.dumps({"amount": 900, "currency": "EUR"}).encode()

        signature = self.bancontact_product_display._sign_bancontact_request(url, body)

        protected_b64, payload_b64, signature_b64 = signature.split(".")
        self.assertFalse(payload_b64, "The payload must be detached")

        # The signature is valid for the published public key
        validation = BancontactSignatureValidation(SimpleNamespace(data=body))
        validation._verify_jws_signature(self.company._bancontact_get_public_jwk(), protected_b64, signature_b64)

        protected = json.loads(validation._b64url_decode(protected_b64))
        self.assertEqual(protected["alg"], "ES256")
        self.assertEqual(protected["kid"], self.company.bancontact_signing_kid)
        self.assertCountEqual(protected["crit"], [const.ISS_KEY, const.IAT_KEY, const.JTI_KEY, const.PATH_KEY, const.SUB_KEY])
        self.assertEqual(protected[const.ISS_KEY], "merchant_id")
        self.assertEqual(protected[const.SUB_KEY], "display_profile_id")
        self.assertEqual(protected[const.PATH_KEY], url)
        self.assertTrue(protected[const.IAT_KEY])
        self.assertTrue(protected[const.JTI_KEY])

    def test_sign_bancontact_request_without_merchant_id(self):
        with self.assertRaises(UserError):
            self.bancontact_product_display._sign_bancontact_request("https://merchant.api.preprod.bancontact.net", b"{}")
