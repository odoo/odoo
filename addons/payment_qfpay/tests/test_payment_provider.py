# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.payment_qfpay.tests.common import QFPayCommon


@tagged("post_install", "-at_install")
class TestPaymentProvider(QFPayCommon):
    def test_signature_calculation_for_outgoing_data(self):
        calculated_signature = self.provider._qfpay_calculate_signature({
            "out_trade_no": self.reference,
            "txamt": "111111",
            "txcurrcd": "HKD",
            "goods_name": "",
        })
        self.assertEqual(calculated_signature, "B8414E0AE7D243FF303D198BAE218195")

    def test_signature_calculation_for_webhook_data(self):
        calculated_signature = self.provider._qfpay_calculate_signature(
            self.webhook_raw_body, is_webhook=True
        )
        self.assertEqual(calculated_signature, self.webhook_signature)
