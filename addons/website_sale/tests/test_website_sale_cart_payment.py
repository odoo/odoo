# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests.common import JsonRpcException, tagged
from odoo.tools import mute_logger

from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.website_sale.tests.common import MockRequest, WebsiteSaleCommon


@tagged('post_install', '-at_install')
class WebsiteSaleCartPayment(PaymentHttpCommon, WebsiteSaleCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.tx = cls.env['payment.transaction'].create({
            'payment_method_id': cls.payment_method_id,
            'amount': cls.amount,
            'currency_id': cls.currency.id,
            'provider_id': cls.provider.id,
            'reference': cls.reference,
            'operation': 'online_redirect',
            'partner_id': cls.partner.id,
        })
        cls.cart.write({'transaction_ids': [Command.set([cls.tx.id])]})

    def test_unpaid_orders_can_be_retrieved(self):
        """ Test that fetching sales orders linked to a payment transaction in the states 'draft',
        'cancel', or 'error' returns the orders. """
        for unpaid_order_tx_state in ('draft', 'cancel', 'error'):
            self.tx.state = unpaid_order_tx_state
            with MockRequest(self.env, website=self.website, sale_order_id=self.cart.id) as request:
                self.assertEqual(
                    request.cart,
                    self.cart,
                    msg=f"The transaction state '{unpaid_order_tx_state}' should not prevent "
                        f"retrieving the linked order.",
                )

    def test_paid_orders_cannot_be_retrieved(self):
        """ Test that fetching sales orders linked to a payment transaction in the states 'pending',
        'authorized', or 'done' returns an empty recordset to prevent updating the paid orders. """
        self.tx.provider_id.support_manual_capture = 'full_only'
        for paid_order_tx_state in ('pending', 'authorized', 'done'):
            self.tx.state = paid_order_tx_state
            with MockRequest(self.env, website=self.website, sale_order_id=self.cart.id) as request:
                self.assertFalse(
                    request.cart,
                    msg=f"The transaction state '{paid_order_tx_state}' should prevent retrieving "
                        f"the linked order.",
                )

    @mute_logger('odoo.http')
    def test_transaction_route_rejects_unexpected_kwarg(self):
        url = self._build_url(f'/shop/payment/transaction/{self.cart.id}')
        route_kwargs = {
            'access_token': self.cart._portal_ensure_token(),
            'partner_id': self.partner.id,  # This should be rejected.
        }
        with self.assertRaises(JsonRpcException, msg='odoo.exceptions.ValidationError'):
            self.make_jsonrpc_request(url, route_kwargs)
