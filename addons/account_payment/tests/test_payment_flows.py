# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.account_payment.tests.common import AccountPaymentCommon


@tagged('post_install', '-at_install')
class TestFlows(AccountPaymentCommon, PaymentHttpCommon):

    def test_invoice_payment_flow(self):
        """Test the payment of an invoice through the payment/pay route"""

        # Pay for this invoice (no impact even if amounts do not match)
        route_values = self._prepare_pay_values()
        route_values['invoice_id'] = self.invoice.id
        tx_context = self._get_tx_checkout_context(**route_values)
        self.assertEqual(tx_context['invoice_id'], self.invoice.id)

        # payment/transaction
        route_values = {
            k: tx_context[k]
            for k in [
                'amount',
                'currency_id',
                'reference_prefix',
                'partner_id',
                'access_token',
                'landing_route',
                'invoice_id',
            ]
        }
        route_values.update({
            'flow': 'direct',
            'payment_option_id': self.provider.id,
            'tokenization_requested': False,
        })
        with mute_logger('odoo.addons.payment.models.payment_transaction'):
            processing_values = self._get_processing_values(**route_values)
        tx_sudo = self._get_tx(processing_values['reference'])
        # Note: strangely, the check
        # self.assertEqual(tx_sudo.invoice_ids, invoice)
        # doesn't work, and cache invalidation doesn't work either.
        self.invoice.invalidate_recordset(['transaction_ids'])
        self.assertEqual(self.invoice.transaction_ids, tx_sudo)
