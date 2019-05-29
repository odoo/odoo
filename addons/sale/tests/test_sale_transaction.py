# -*- coding: utf-8 -*-
from odoo import tests
from odoo.addons.account.tests.account_test_classes import AccountingTestCase


@tests.tagged('post_install', '-at_install')
class TestSaleTransaction(AccountingTestCase):
    def test_sale_invoicing_from_transaction(self):
        ''' Test the following scenario:
        - Create a sale order
        - Create a transaction for the sale order.
        - Confirm the transaction but no invoice generated automatically.
        - Create manually an invoice for this sale order.
        => The invoice must be paid.
        '''
        product = self.env['product.product'].create({
            'name': 'Product A',
        })

        order = self.env['sale.order'].create({
            'partner_id': self.env.ref('base.res_partner_1').id,
            'order_line': [
                (0, False, {
                    'product_id': product.id,
                    'name': '1 Product',
                    'price_unit': 100.0,
                }),
            ],
        })

        transaction = order._create_payment_transaction({
            'acquirer_id': self.env.ref('payment.payment_acquirer_transfer').id,
        })
        transaction._set_transaction_done()
        transaction._post_process_after_done()

        # Assert a posted payment has been generated at this point.
        self.assertTrue(transaction.payment_id)
        self.assertEqual(transaction.payment_id.state, 'posted')

        invoice = order._create_invoices()
        invoice.post()

        self.assertEqual(invoice.invoice_payment_state, 'paid')
