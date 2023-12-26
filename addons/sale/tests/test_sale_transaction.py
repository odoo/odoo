# -*- coding: utf-8 -*-
from odoo import tests
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tools import mute_logger


@tests.tagged('post_install', '-at_install')
class TestSaleTransaction(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.company_data['company'].country_id = cls.env.ref('base.us')

        cls.order = cls.env['sale.order'].create({
            'partner_id': cls.partner_a.id,
            'order_line': [
                (0, False, {
                    'product_id': cls.product_a.id,
                    'name': '1 Product',
                    'price_unit': 100.0,
                }),
            ],
        })
        cls.env.ref('payment.payment_acquirer_transfer').journal_id = cls.company_data['default_journal_cash']

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

        # Doesn't work with stock installed.
        # invoice = self.order._create_invoices()
        # invoice.post()
        #
        # self.assertTrue(invoice.payment_state in ('in_payment', 'paid'), "Invoice should be paid")

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
        self.product_a.invoice_policy = 'delivery'
        self.transaction._set_transaction_done()
        with mute_logger('odoo.addons.sale.models.payment'):
            self.transaction.sudo()._post_process_after_done()
        self.assertEqual(self.order.state, 'draft', 'a partial transaction with automatic invoice and invoice_policy = delivery should not validate a quote')
