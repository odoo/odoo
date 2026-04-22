# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo.tests import tagged

from odoo.addons.payment_qfpay import const
from odoo.addons.payment_qfpay.tests.common import QFPayCommon


@tagged("post_install", "-at_install")
class TestPaymentProvider(QFPayCommon):
    def test_get_inline_form_values(self):
        """Test that inline form values contain all SDK configuration entries."""
        values = json.loads(self.provider._qfpay_get_inline_form_values("unionpay"))

        self.assertEqual(values["payment_method_code"], "unionpay")
        self.assertEqual(values["picker_payment_type"], const.PAYMENT_PICKER_TYPES["unionpay"])
        self.assertIn("sdk_url", values)
        self.assertIn("sdk_env", values)
        self.assertIn("sdk_region", values)

    def test_build_request_headers(self):
        """Test that request headers include app code and computed signature."""
        payload = {"out_trade_no": self.reference, "txamt": "75000"}

        headers = self.provider._build_request_headers("POST", "/trade/v1/query", payload)

        self.assertEqual(headers["X-QF-APPCODE"], self.provider.qfpay_app_code)
        self.assertEqual(headers["X-QF-SIGN"], self.provider._qfpay_calculate_signature(payload))
