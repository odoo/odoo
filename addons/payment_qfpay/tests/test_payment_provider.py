# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.payment_qfpay.tests.common import QFPayCommon


@tagged("post_install", "-at_install")
class TestPaymentProvider(QFPayCommon):
    def test_build_request_headers(self):
        """Test that request headers include app code and computed signature."""
        payload = {"out_trade_no": self.reference, "txamt": "75000"}

        headers = self.provider._build_request_headers("POST", "/trade/v1/query", payload)

        self.assertEqual(headers["X-QF-APPCODE"], self.provider.qfpay_app_code)
        self.assertEqual(headers["X-QF-SIGN"], self.provider._qfpay_calculate_signature(payload))
