# -*- coding: utf-8 -*-
from odoo import tests
from odoo.addons.account.tests.account_test_classes import AccountingTestCase
from odoo.tools import mute_logger


@tests.tagged('post_install', '-at_install')
class TestSaleTransaction(AccountingTestCase):

    def setUp(self):
        super(TestSaleTransaction, self).setUp()
        self.product = self.env['product.product'].create({
            'name': 'Product A',
        })
        self.order = self.env['sale.order'].create({
            'partner_id': self.env.ref('base.res_partner_1').id,
            'order_line': [
                (0, False, {
                    'product_id': self.product.id,
                    'name': '1 Product',
                    'price_unit': 100.0,
                }),
            ],
        })

        self.transaction = self.order._create_payment_transaction({
            'acquirer_id': self.env.ref('payment.payment_acquirer_transfer').id,
        })

    def test_sale_invoicing_from_transaction(self):
        ''' Test the following scenario:
        - Create a sale order
        - Create a transaction for the sale order.
        - Confirm the transaction but no invoice generated automatically.
        - Create manually an invoice for this sale order.
        => The invoice must be paid.
        '''
        self.transaction._set_transaction_done()
        self.transaction._post_process_after_done()

        # Assert a posted payment has been generated at this point.
        self.assertTrue(self.transaction.payment_id)
        self.assertEqual(self.transaction.payment_id.state, 'posted')

        invoice = self.order._create_invoices()
        invoice.post()

        self.assertEqual(invoice.invoice_payment_state, 'paid')

    def test_sale_transaction_mismatch(self):
        """Test that a transaction for the incorrect amount does not validate the SO."""
        # modify order total
        self.order.order_line[0].price_unit = 200.0
        self.transaction._set_transaction_done()
        with mute_logger('odoo.addons.sale.models.payment'):
            self.transaction._post_process_after_done()
        self.assertEqual(self.order.state, 'draft', 'a transaction for an incorrect amount should not validate a quote')

    def test_sale_transaction_partial_delivery(self):
        """Test that with automatic invoice and invoicing policy based on delivered quantity, a transaction for the partial
        amount does not validate the SO."""
        # set automatic invoice
        self.env['ir.config_parameter'].sudo().set_param('sale.automatic_invoice', 'True')
        # modify order total
        self.order.order_line[0].price_unit = 200.0
        # invoicing policy is based on delivered quantity
        self.product.invoice_policy = 'delivery'
        self.transaction._set_transaction_done()
        with mute_logger('odoo.addons.sale.models.payment'):
            self.transaction.sudo()._post_process_after_done()
        self.assertEqual(self.order.state, 'draft', 'a partial transaction with automatic invoice and invoice_policy = delivery should not validate a quote')
