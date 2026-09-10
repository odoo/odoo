# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.payment_redsys.tests.common import RedsysCommon


@tagged("post_install", "-at_install")
class TestPaymentProvider(RedsysCommon):
    def test_calculate_signature_returns_correct_signature(self):
        signature = self.provider._redsys_calculate_signature(
            self.encoded_merchant_parameter, self.reference, self.provider.redsys_secret_key
        )
        self.assertEqual(signature, self.payment_data_signature)
