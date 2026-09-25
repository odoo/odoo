# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.payment_ecpay.tests.common import EcpayCommon


@tagged("post_install", "-at_install")
class TestPaymentProvider(EcpayCommon):
    def test_calculate_signature_without_language_returns_correct_signature(self):
        self.env["res.lang"]._activate_lang("zh_TW")
        tx = self._create_transaction(
            "redirect", payment_method_id=self.provider._get_pm_from_code("card").id
        )
        rendering_values = tx.with_context(lang="zh_TW")._get_specific_rendering_values(None)
        signature_data = dict(rendering_values["url_params"])
        signature_data.pop("CheckMacValue", None)
        expected_mac = tx.provider_id._ecpay_calculate_signature(signature_data)
        self.assertEqual(rendering_values["url_params"]["CheckMacValue"], expected_mac)

    def test_calculate_signature_returns_correct_signature(self):
        signature = self.provider._ecpay_calculate_signature(self.payment_result_data)
        self.assertEqual(signature, self.webhook_payment_data_signature)
