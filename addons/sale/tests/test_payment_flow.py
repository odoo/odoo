# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment.tests.common import PaymentCommon
from odoo.addons.payment.tests.http_common import PaymentHttpCommon


@tagged('-at_install', 'post_install')
class TestSalePayment(PaymentCommon, PaymentHttpCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.pricelist = cls.env['product.pricelist'].search([
            ('currency_id', '=', cls.currency.id)], limit=1)

        if not cls.pricelist:
            cls.pricelist = cls.env['product.pricelist'].create({
                'name': 'Test Pricelist (%s)' % (cls.currency.name),
                'currency_id': cls.currency.id,
            })

        cls.sale_product = cls.env['product.product'].create({
            'sale_ok': True,
            'name': "Test Product",
        })

        cls.order = cls.env['sale.order'].create({
            'partner_id': cls.partner.id,
            'pricelist_id': cls.pricelist.id,
            'order_line': [Command.create({
                'product_id': cls.sale_product.id,
                'product_uom_qty': 5,
                'price_unit': 20,
            })],
        })

        cls.partner = cls.order.partner_invoice_id

    def test_11_so_payment_link(self):
        # test customized /payment/pay route with sale_order_id param
        self.amount = self.order.amount_total
        route_values = self._prepare_pay_values()
        route_values['sale_order_id'] = self.order.id

        tx_context = self.get_tx_checkout_context(**route_values)

        self.assertEqual(tx_context['currency_id'], self.order.currency_id.id)
        self.assertEqual(tx_context['partner_id'], self.order.partner_invoice_id.id)
        self.assertEqual(tx_context['amount'], self.order.amount_total)
        self.assertEqual(tx_context['sale_order_id'], self.order.id)

        route_values.update({
            'flow': 'direct',
            'payment_option_id': self.acquirer.id,
            'tokenization_requested': False,
            'validation_route': False,
            'reference_prefix': None, # Force empty prefix to fallback on SO reference
            'landing_route': tx_context['landing_route'],
            'amount': tx_context['amount'],
            'currency_id': tx_context['currency_id'],
        })

        with mute_logger('odoo.addons.payment.models.payment_transaction'):
            processing_values = self.get_processing_values(**route_values)
        tx_sudo = self._get_tx(processing_values['reference'])

        self.assertEqual(tx_sudo.sale_order_ids, self.order)
        self.assertEqual(tx_sudo.amount, self.amount)
        self.assertEqual(tx_sudo.partner_id, self.order.partner_invoice_id)
        self.assertEqual(tx_sudo.company_id, self.order.company_id)
        self.assertEqual(tx_sudo.currency_id, self.order.currency_id)
        self.assertEqual(tx_sudo.reference, self.order.name)

        # Check validation of transaction correctly confirms the SO
        self.assertEqual(self.order.state, 'draft')
        tx_sudo._set_done()
        tx_sudo._finalize_post_processing()
        self.assertEqual(self.order.state, 'sale')
        self.assertTrue(tx_sudo.payment_id)
        self.assertEqual(tx_sudo.payment_id.state, 'posted')

    def test_so_payment_link_with_different_partner_invoice(self):
        # test customized /payment/pay route with sale_order_id param
        # partner_id and partner_invoice_id different on the so
        self.order.partner_invoice_id = self.portal_partner
        self.partner = self.order.partner_invoice_id
        route_values = self._prepare_pay_values()
        route_values['sale_order_id'] = self.order.id

        tx_context = self.get_tx_checkout_context(**route_values)
        self.assertEqual(tx_context['partner_id'], self.order.partner_invoice_id.id)

    def test_12_so_partial_payment_link(self):
        # test customized /payment/pay route with sale_order_id param
        # partial amount specified
        self.amount = self.order.amount_total / 2.0
        route_values = self._prepare_pay_values()
        route_values['sale_order_id'] = self.order.id

        tx_context = self.get_tx_checkout_context(**route_values)

        self.assertEqual(tx_context['reference_prefix'], self.reference)
        self.assertEqual(tx_context['currency_id'], self.order.currency_id.id)
        self.assertEqual(tx_context['partner_id'], self.order.partner_invoice_id.id)
        self.assertEqual(tx_context['amount'], self.amount)
        self.assertEqual(tx_context['sale_order_id'], self.order.id)

        route_values.update({
            'flow': 'direct',
            'payment_option_id': self.acquirer.id,
            'tokenization_requested': False,
            'validation_route': False,
            'reference_prefix': tx_context['reference_prefix'],
            'landing_route': tx_context['landing_route'],
        })
        with mute_logger('odoo.addons.payment.models.payment_transaction'):
            processing_values = self.get_processing_values(**route_values)
        tx_sudo = self._get_tx(processing_values['reference'])

        self.assertEqual(tx_sudo.sale_order_ids, self.order)
        self.assertEqual(tx_sudo.amount, self.amount)
        self.assertEqual(tx_sudo.partner_id, self.order.partner_invoice_id)
        self.assertEqual(tx_sudo.company_id, self.order.company_id)
        self.assertEqual(tx_sudo.currency_id, self.order.currency_id)
        self.assertEqual(tx_sudo.reference, self.reference)

        tx_sudo._set_done()
        with mute_logger('odoo.addons.sale.models.payment_transaction'):
            tx_sudo._finalize_post_processing()
        self.assertEqual(self.order.state, 'draft') # Only a partial amount was paid

        # Pay the remaining amount
        route_values = self._prepare_pay_values()
        route_values['sale_order_id'] = self.order.id

        tx_context = self.get_tx_checkout_context(**route_values)

        self.assertEqual(tx_context['reference_prefix'], self.reference)
        self.assertEqual(tx_context['currency_id'], self.order.currency_id.id)
        self.assertEqual(tx_context['partner_id'], self.order.partner_id.id)
        self.assertEqual(tx_context['amount'], self.amount)
        self.assertEqual(tx_context['sale_order_id'], self.order.id)

        route_values.update({
            'flow': 'direct',
            'payment_option_id': self.acquirer.id,
            'tokenization_requested': False,
            'validation_route': False,
            'reference_prefix': tx_context['reference_prefix'],
            'landing_route': tx_context['landing_route'],
        })
        with mute_logger('odoo.addons.payment.models.payment_transaction'):
            processing_values = self.get_processing_values(**route_values)
        tx2_sudo = self._get_tx(processing_values['reference'])

        self.assertEqual(tx2_sudo.sale_order_ids, self.order)
        self.assertEqual(tx2_sudo.amount, self.amount)
        self.assertEqual(tx2_sudo.partner_id, self.order.partner_invoice_id)
        self.assertEqual(tx2_sudo.company_id, self.order.company_id)
        self.assertEqual(tx2_sudo.currency_id, self.order.currency_id)

        # We are paying a second time with the same reference (prefix)
        # a suffix is added to respect unique reference constraint
        reference = self.reference + "-1"
        self.assertEqual(tx2_sudo.reference, reference)
        self.assertEqual(self.order.state, 'draft')
        self.assertEqual(self.order.transaction_ids, tx_sudo + tx2_sudo)

    def test_13_sale_automatic_partial_payment_link_delivery(self):
        """Test that with automatic invoice and invoicing policy based on delivered quantity, a transaction for the partial
        amount does not validate the SO."""
        # set automatic invoice
        self.env['ir.config_parameter'].sudo().set_param('sale.automatic_invoice', 'True')
        # invoicing policy is based on delivered quantity
        self.sale_product.invoice_policy = 'delivery'

        self.amount = self.order.amount_total / 2.0
        route_values = self._prepare_pay_values()
        route_values['sale_order_id'] = self.order.id

        tx_context = self.get_tx_checkout_context(**route_values)

        route_values.update({
            'flow': 'direct',
            'payment_option_id': self.acquirer.id,
            'tokenization_requested': False,
            'validation_route': False,
            'reference_prefix': tx_context['reference_prefix'],
            'landing_route': tx_context['landing_route'],
        })
        with mute_logger('odoo.addons.payment.models.payment_transaction'):
            processing_values = self.get_processing_values(**route_values)
        tx_sudo = self._get_tx(processing_values['reference'])

        tx_sudo._set_done()
        with mute_logger('odoo.addons.sale.models.payment_transaction'):
            tx_sudo._finalize_post_processing()

        self.assertEqual(self.order.state, 'draft', 'a partial transaction with automatic invoice and invoice_policy = delivery should not validate a quote')
