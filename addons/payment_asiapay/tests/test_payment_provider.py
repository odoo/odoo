# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.payment_asiapay import const
from odoo.addons.payment_asiapay.tests.common import AsiaPayCommon


@tagged('post_install', '-at_install')
class TestPaymentProvider(AsiaPayCommon):

    def test_incompatible_with_unsupported_currencies(self):
        """ Test that AsiaPay providers are filtered out from compatible providers when the currency
        is not supported. """
        compatible_providers = self.env['payment.provider']._get_compatible_providers(
            self.env.company.id, self.partner.id, self.amount, currency_id=self.env.ref('base.AFN').id
        )
        self.assertNotIn(self.asiapay, compatible_providers)

    def test_signature_calculation_for_outgoing_data(self):
        """ Test that the calculated signature matches the expected signature for outgoing data. """
        calculated_signature = self.asiapay._asiapay_calculate_signature(
            {
                'merchant_id': self.asiapay.asiapay_merchant_id,
                'amount': self.amount,
                'reference': self.reference,
                'currency_code': const.CURRENCY_MAPPING[self.currency.name],
                'payment_type': 'N',
            },
            incoming=False
        )
        self.assertEqual(calculated_signature, '41667af8f428b5a55f44e14e5ab942f57da1ea31')

    def test_signature_calculation_for_incoming_data(self):
        """ Test that the calculated signature matches the expected signature for incoming data. """
        calculated_signature = self.asiapay._asiapay_calculate_signature(
            self.webhook_payment_data, incoming=True
        )
        self.assertEqual(calculated_signature, '3e5bf55d9a23969130a6686db7aa4f0230956d0a')
