# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.models import Command
from odoo.tests.common import JsonRpcException, tagged
from odoo.tools import mute_logger

from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.website.tools import MockRequest


@tagged('post_install', '-at_install')
class WebsiteSaleCartPayment(PaymentHttpCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.website = cls.env['website'].get_current_website()
        with MockRequest(cls.env, website=cls.website):
            cls.order = cls.website.sale_get_order(force_create=True)  # Create the cart to retrieve
        cls.tx = cls.env['payment.transaction'].create({
            'payment_method_id': cls.payment_method_id,
            'amount': cls.amount,
            'currency_id': cls.currency.id,
            'provider_id': cls.provider.id,
            'reference': cls.reference,
            'operation': 'online_redirect',
            'partner_id': cls.partner.id,
        })
        cls.order.write({'transaction_ids': [Command.set([cls.tx.id])]})

    def test_unpaid_orders_can_be_retrieved(self):
        """ Test that fetching sales orders linked to a payment transaction in the states 'draft',
        'cancel', or 'error' returns the orders. """
        for unpaid_order_tx_state in ('draft', 'cancel', 'error'):
            self.tx.state = unpaid_order_tx_state
            with MockRequest(self.env, website=self.website, sale_order_id=self.order.id):
                self.assertEqual(
                    self.website.sale_get_order(),
                    self.order,
                    msg=f"The transaction state '{unpaid_order_tx_state}' should not prevent "
                        f"retrieving the linked order.",
                )

    def test_paid_orders_cannot_be_retrieved(self):
        """ Test that fetching sales orders linked to a payment transaction in the states 'pending',
        'authorized', or 'done' returns an empty recordset to prevent updating the paid orders. """
        self.tx.provider_id.support_manual_capture = 'full_only'
        for paid_order_tx_state in ('pending', 'authorized', 'done'):
            self.tx.state = paid_order_tx_state
            with MockRequest(self.env, website=self.website, sale_order_id=self.order.id):
                self.assertFalse(
                    self.website.sale_get_order(),
                    msg=f"The transaction state '{paid_order_tx_state}' should prevent retrieving "
                        f"the linked order.",
                )

    @mute_logger('odoo.http')
    def test_transaction_route_rejects_unexpected_kwarg(self):
        url = self._build_url(f'/shop/payment/transaction/{self.order.id}')
        route_kwargs = {
            'access_token': self.order._portal_ensure_token(),
            'partner_id': self.partner.id,  # This should be rejected.
        }
        with self.assertRaises(JsonRpcException, msg='odoo.exceptions.ValidationError'):
            self.make_jsonrpc_request(url, route_kwargs)

    def test_cart_updated_after_payment_initiation_is_not_confirmed(self):
        """Test that a cart updated after the payment is initiated is not confirmed with the
        initial payment amount, even if it covers the prepayment percentage."""
        product = self.env["product.product"].create({"name": "Test Product", "list_price": 100.0})
        self.order.company_id.prepayment_percent = 0.2
        self.order.write({
            "order_line": [Command.create({"product_id": product.id})],
            "require_payment": True,
        })
        self.tx.amount = self.order.amount_total
        self.order.order_line.product_uom_qty = 2  # Update the cart from another tab.
        self.tx.state = "done"
        self.tx._check_amount_and_confirm_order()
        self.assertEqual(self.order.state, "draft")
