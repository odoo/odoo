# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.fields import Command
from odoo.tests import JsonRpcException, tagged
from odoo.tools import mute_logger

from odoo.addons.account_payment.tests.common import AccountPaymentCommon
from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.sale.tests.common import SaleCommon


@tagged('post_install', '-at_install')
class TestSaleStockPortal(AccountPaymentCommon, PaymentHttpCommon, SaleCommon):

    def _sign_on_portal(self, order):
        return self.make_jsonrpc_request(self._build_url(f'/my/orders/{order.id}/accept'), {
            'access_token': order._portal_ensure_token(),
            'signature': 'R0lGODdhAQABAIAAAP///////ywAAAAAAQABAAACAkQBADs=',  # BASE64 of a simple image
        })

    def test_portal_sign_order_without_warehouse(self):
        """Check that signing a quotation online is refused when the company has no warehouse to deliver it from."""
        self.env['stock.warehouse'].search([('company_id', '=', self.sale_order.company_id.id)]).active = False
        self.sale_order.warehouse_id = False
        self.sale_order.write({'require_signature': True, 'require_payment': False})

        result = self._sign_on_portal(self.sale_order)

        self.assertEqual(result['error'], "This order cannot be confirmed online. Please contact us.")
        self.assertEqual(self.sale_order.state, 'draft')
        self.assertFalse(self.sale_order.signature)

    def test_portal_sign_service_order_without_warehouse(self):
        """Check that a quotation with nothing to deliver can still be signed online when the company has no warehouse."""
        self.env['stock.warehouse'].search([('company_id', '=', self.sale_order.company_id.id)]).active = False
        order = self._create_so(
            order_line=[Command.create({'product_id': self.service_product.id})],
            require_signature=True,
        )

        result = self._sign_on_portal(order)

        self.assertNotIn('error', result)
        self.assertEqual(order.state, 'sale')

    def test_payment_link_for_order_without_warehouse(self):
        """Check that the salesperson cannot generate a payment link for a quotation the company has no warehouse to deliver."""
        self.env['stock.warehouse'].search([('company_id', '=', self.sale_order.company_id.id)]).active = False
        self.sale_order.warehouse_id = False
        wizard = self.env['payment.link.wizard'].with_context(
            active_model='sale.order', active_id=self.sale_order.id,
        ).create({})

        self.assertEqual(wizard.warning_message, "A warehouse is required to confirm this order.")

    @mute_logger('odoo.http')
    def test_portal_pay_order_without_warehouse(self):
        """Check that paying a quotation online is refused before any transaction is created when the company has no warehouse."""
        self.env['stock.warehouse'].search([('company_id', '=', self.sale_order.company_id.id)]).active = False
        self.sale_order.warehouse_id = False
        self.sale_order.write({'require_signature': False, 'require_payment': True})

        with self.assertRaisesRegex(JsonRpcException, 'odoo.exceptions.ValidationError'):
            self.make_jsonrpc_request(self._build_url(f'/my/orders/{self.sale_order.id}/transaction'), {
                'access_token': self.sale_order._portal_ensure_token(),
                'provider_id': self.provider.id,
                'payment_method_id': self.payment_method_id,
                'token_id': None,
                'amount': self.sale_order.amount_total,
                'flow': 'direct',
                'tokenization_requested': False,
                'landing_route': self.sale_order.get_portal_url(),
                'is_validation': False,
            })

        self.assertFalse(self.sale_order.transaction_ids)
