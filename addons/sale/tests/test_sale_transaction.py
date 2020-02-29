# -*- coding: utf-8 -*-
from odoo import tests
from odoo.addons.account.tests.common import AccountTestCommon
from odoo.tools import mute_logger

@tests.tagged('post_install', '-at_install')
class TestSaleTransaction(AccountTestCommon):
    @classmethod
    def setUpClass(cls):
        super(TestSaleTransaction, cls).setUpClass()
        cls.product = cls.env['product.product'].create({
            'name': 'Product A',
        })
        cls.order = cls.env['sale.order'].create({
            'partner_id': cls.env['res.partner'].create({'name': 'A partner'}).id,
            'order_line': [
                (0, False, {
                    'product_id': cls.product.id,
                    'name': '1 Product',
                    'price_unit': 100.0,
                }),
            ],
        })
        cls.env.ref('payment.payment_acquirer_transfer').journal_id = cls.cash_journal
        if not cls.env.user.company_id.country_id:
            cls.env.user.company_id.country_id = cls.env.ref('base.us')

        cls.transaction = cls.order._create_payment_transaction({
            'acquirer_id': cls.env.ref('payment.payment_acquirer_transfer').id,
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

        self.assertEqual(invoice.payment_state, 'paid')

    def test_sale_transaction_mismatch(self):
        """Test that a transaction for the incorrect amount does not validate the SO."""
        # modify order total
        self.order.order_line[0].price_unit = 200.0
        self.transaction._set_transaction_done()
        with mute_logger('odoo.addons.sale.models.payment'):
            self.transaction._post_process_after_done()
        self.assertEqual(self.order.state, 'draft', 'a transaction for an incorrect amount should not validate a quote')
