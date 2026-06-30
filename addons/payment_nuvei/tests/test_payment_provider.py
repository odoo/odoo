# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.payment_nuvei.tests.common import NuveiCommon


@tagged('post_install', '-at_install')
class TestPaymentProvider(NuveiCommon):

    def test_incompatible_with_unsupported_currencies(self):
        """ Test that Nuvei providers are filtered out from compatible providers when the currency
        is not supported. """
        currency_id = self.env.ref('base.AFN').id
        compatible_providers = self.env['payment.provider']._get_compatible_providers(
            self.env.company.id, self.partner.id, self.amount, currency_id=currency_id
        )
        self.assertNotIn(self.provider, compatible_providers)

    def test_signature_calculation_for_outgoing_data(self):
        """ Test that the calculated signature matches the expected signature for outgoing data. """
        calculated_signature = self.provider._nuvei_calculate_signature(
            {
                'encoding': 'UTF-8',
                'item_amount_1': self.amount,
                'item_name_1': self.reference,
                'item_quantity_1': 1,
                'invoice_id': self.reference,
                'merchant_id': self.provider.nuvei_merchant_identifier,
                'merchant_site_id': self.provider.nuvei_site_identifier,
                'payment_method_mode': 'filter',
                'payment_method': 'unknown',
                'total_amount': self.amount,
                'version': '4.0.0',
            },
            incoming=False
        )
        expected_signature = '414cd27426090aaea54e29396bc021cc5d965bd3dddd06be853e4554e985386f'
        self.assertEqual(calculated_signature, expected_signature)

    def test_signature_calculation_for_incoming_data(self):
        """ Test that the calculated signature matches the expected signature for incoming data. """
        calculated_signature = self.provider._nuvei_calculate_signature(
            self.payment_data, incoming=True
        )
        received_signature = self.payment_data.get('advanceResponseChecksum')
        self.assertEqual(calculated_signature, received_signature)

