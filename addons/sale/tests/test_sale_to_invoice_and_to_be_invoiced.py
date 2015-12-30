# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common


class TestSaleOrderInvoicing(common.TransactionCase):

    def setUp(self):
        super(TestSaleOrderInvoicing, self).setUp()

        self.SaleAdvancePaymentInv = self.env['sale.advance.payment.inv']
        self.AccountAccount = self.env['account.account']

        self.product_id_1 = self.env.ref('product.product_product_8')
        self.product_id_2 = self.env.ref('product.product_product_11')
        self.partner = self.env.ref('base.res_partner_1')

        # Usefull accounts
        user_type_id = self.env.ref('account.data_account_type_revenue')
        self.account_rev_id = self.AccountAccount.create({'code': 'X2020', 'name': 'Sales - Test Sales Account', 'user_type_id': user_type_id.id, 'reconcile': True})
        user_type_id = self.env.ref('account.data_account_type_receivable')
        self.account_recv_id = self.AccountAccount.create({'code': 'X1012', 'name': 'Sales - Test Reicv Account', 'user_type_id': user_type_id.id, 'reconcile': True})
        self.partner.property_account_receivable_id = self.account_recv_id

        # Create Sales Journal
        company = self.env.ref('base.main_company')
        self.env['account.journal'].create({'name': 'Sales Journal - Test', 'code': 'STSJ', 'type': 'sale', 'company_id': company.id})

    def test_sale_to_invoice_and_to_be_invoiced(self):
        """ Testing amount to invoice and amount to be invoiced. """

        # In order to test I create sales order and confirmed it.
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'partner_invoice_id': self.partner.id,
            'partner_shipping_id': self.partner.id,
            'order_line': [(0, 0, {'name': self.product_id_1.name, 'product_id': self.product_id_1.id, 'product_uom_qty': 2, 'product_uom': self.product_id_1.uom_id.id, 'price_unit': 100}), (0, 0, {'name': self.product_id_2.name, 'product_id': self.product_id_2.id, 'product_uom_qty': 2, 'product_uom': self.product_id_2.uom_id.id, 'price_unit': 300})],
            'pricelist_id': self.env.ref('product.list0').id,
        })

        context = {"active_model": 'sale.order', "active_ids": [order.id], "active_id": order.id}
        order.with_context(context).action_confirm()

        # Now I create invoice.
        self.advance_product = self.env.ref('sale.advance_product_0')
        self.advance_product.property_account_income_id = self.account_rev_id

        payment = self.SaleAdvancePaymentInv.create({
            'advance_payment_method': 'fixed',
            'amount': 500,
            'product_id': self.advance_product.id,
        })
        payment.with_context(context).create_invoices()
        invoice_1 = order.invoice_ids[0]

        # Lets create one more invoice.

        payment = self.SaleAdvancePaymentInv.create({
            'advance_payment_method': 'fixed',
            'amount': 300,
            'product_id': self.advance_product.id,
        })
        payment.with_context(context).create_invoices()
        invoice_2 = order.invoice_ids[1]

        self.assertEqual(sum(order.order_line.mapped('amt_to_invoice')), 800.0, 'Sale: the Amount To Invoice for the sale order should be 800.0.')
        self.assertEqual(sum(order.order_line.mapped('amt_invoiced')), 0.0, 'Sale: the Amount Invoiced for the sale order should be 0.0.')

        # Now I validate invoice_1.
        invoice_1.invoice_validate()

        self.assertEqual(sum(order.order_line.mapped('amt_to_invoice')), 300.0, 'Sale: the Amount To Invoice for the sale order should be 300.0.')
        self.assertEqual(sum(order.order_line.mapped('amt_invoiced')), 500.0, 'Sale: the Amount Invoiced for the sale order should be 500.0.')

        # Now I validate invoice_2.
        invoice_2.invoice_validate()

        self.assertEqual(sum(order.order_line.mapped('amt_to_invoice')), 0.0, 'Sale: the Amount To Invoice for the sale order should be 0.0.')
        self.assertEqual(sum(order.order_line.mapped('amt_invoiced')), 800.0, 'Sale: the Amount Invoiced for the sale order should be 800.0.')

        # Lets create a refund invoice for invoice_1.
        # I refund the invoice Using Refund Button.
        context = {"active_model": 'account.invoice', "active_ids": [invoice_1.id], "active_id": invoice_1.id}
        self.account_invoice_refund_1 = self.env['account.invoice.refund'].with_context(context).create(dict(
            description='Refund for Invoice 1',
            filter_refund='refund'
        ))

        # I clicked on refund button.
        self.account_invoice_refund_1.with_context(context).invoice_refund()
        invoice_1.refund_invoice_ids and invoice_1.refund_invoice_ids[0].invoice_validate()

        self.assertEqual(sum(order.order_line.mapped('amt_to_invoice')), 0.0, 'Sale: the Amount To Invoice for the sale order should be 0.0.')
        self.assertEqual(sum(order.order_line.mapped('amt_invoiced')), 300.0, 'Sale: the Amount Invoiced for the sale order should be 300.0.')

        # Lets create a refund invoice for invoice_2.
        # I refund the invoice Using Refund Button.
        context = {"active_model": 'account.invoice', "active_ids": [invoice_2.id], "active_id": invoice_2.id}
        self.account_invoice_refund_2 = self.env['account.invoice.refund'].with_context(context).create(dict(
            description='Refund for Invoice 2',
            filter_refund='refund'
        ))

        # I clicked on refund button.
        self.account_invoice_refund_2.with_context(context).invoice_refund()
        invoice_2.refund_invoice_ids and invoice_2.refund_invoice_ids[0].invoice_validate()

        self.assertEqual(sum(order.order_line.mapped('amt_to_invoice')), 0.0, 'Sale: the Amount To Invoice for the sale order should be 0.0.')
        self.assertEqual(sum(order.order_line.mapped('amt_invoiced')), 0.0, 'Sale: the Amount Invoiced for the sale order should be 0.0.')
