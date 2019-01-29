# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.account.tests.account_test_classes import AccountingTestCase


class TestSaleOrderInvoicing(AccountingTestCase):

    def test_sale_to_invoice_and_to_be_invoiced(self):
        """ Testing amount to invoice and amount to be invoiced, with advances. """

        partner = self.env.ref('base.res_partner_1')
        partner.property_account_receivable_id = self.env['account.account'].search(
            [('user_type_id', '=', self.env.ref('account.data_account_type_revenue').id)], limit=1)
        product_1 = self.env.ref('product.product_product_8')
        product_2 = self.env.ref('product.product_product_11')

        # In order to test I create sales order and confirmed it.
        order = self.env['sale.order'].create({
            'partner_id': partner.id,
            'partner_invoice_id': partner.id,
            'partner_shipping_id': partner.id,
            'order_line': [
                (0, 0, {
                    'name': product_1.name,
                    'product_id': product_1.id,
                    'product_uom_qty': 2,
                    'qty_delivered': 2,
                    'product_uom': product_1.uom_id.id,
                    'price_unit': 100
                }),
                (0, 0, {
                    'name': product_2.name,
                    'product_id': product_2.id,
                    'product_uom_qty': 2,
                    'qty_delivered': 2,
                    'product_uom': product_2.uom_id.id,
                    'price_unit': 300
                })
            ],
            'pricelist_id': self.env.ref('product.list0').id,
        })

        context = {"active_model": 'sale.order', "active_ids": [order.id], "active_id": order.id}
        order.with_context(context).action_confirm()

        # Now I create invoice.
        advance_product = self.env.ref('sale.advance_product_0')
        advance_product.property_account_income_id = self.env['account.account'].search(
            [('user_type_id', '=', self.env.ref('account.data_account_type_revenue').id)], limit=1)

        payment = self.env['sale.advance.payment.inv'].create({
            'advance_payment_method': 'fixed',
            'amount': 500,
            'product_id': advance_product.id,
        })
        payment.with_context(context).create_invoices()
        invoice_1 = order.invoice_ids[0]

        # Lets create one more invoice.

        payment = self.env['sale.advance.payment.inv'].create({
            'advance_payment_method': 'fixed',
            'amount': 300,
            'product_id': advance_product.id,
        })
        payment.with_context(context).create_invoices()
        invoice_2 = order.invoice_ids[1]

        self.assertEqual(sum(order.order_line.mapped('amt_to_invoice')), 800.0, 'Sale: the Amount To Invoice for the sale order should be 800.0.')
        self.assertEqual(sum(order.order_line.mapped('amt_invoiced')), 0.0, 'Sale: the Amount Invoiced for the sale order should be 0.0.')

        # Now I validate invoice_1.
        invoice_1.action_invoice_open()

        self.assertEqual(sum(order.order_line.mapped('amt_to_invoice')), 300.0, 'Sale: the Amount To Invoice for the sale order should be 300.0.')
        self.assertEqual(sum(order.order_line.mapped('amt_invoiced')), 500.0, 'Sale: the Amount Invoiced for the sale order should be 500.0.')

        # Now I validate invoice_2.
        invoice_2.action_invoice_open()

        self.assertEqual(sum(order.order_line.mapped('amt_to_invoice')), 0.0, 'Sale: the Amount To Invoice for the sale order should be 0.0.')
        self.assertEqual(sum(order.order_line.mapped('amt_invoiced')), 800.0, 'Sale: the Amount Invoiced for the sale order should be 800.0.')

        # Lets create a refund invoice for invoice_1.
        # I refund the invoice Using Refund Button.
        context = {"active_model": 'account.invoice', "active_ids": [invoice_1.id], "active_id": invoice_1.id}
        account_invoice_refund_1 = self.env['account.invoice.refund'].with_context(context).create(dict(
            description='Refund for Invoice 1',
            filter_refund='refund'
        ))

        # I clicked on refund button.
        account_invoice_refund_1.with_context(context).invoice_refund()
        invoice_1.refund_invoice_ids and invoice_1.refund_invoice_ids[0].action_invoice_open()

        self.assertEqual(sum(order.order_line.mapped('amt_to_invoice')), 0.0, 'Sale: the Amount To Invoice for the sale order should be 0.0.')
        self.assertEqual(sum(order.order_line.mapped('amt_invoiced')), 300.0, 'Sale: the Amount Invoiced for the sale order should be 300.0.')

        # Lets create a refund invoice for invoice_2.
        # I refund the invoice Using Refund Button.
        context = {"active_model": 'account.invoice', "active_ids": [invoice_2.id], "active_id": invoice_2.id}
        account_invoice_refund_2 = self.env['account.invoice.refund'].with_context(context).create(dict(
            description='Refund for Invoice 2',
            filter_refund='refund'
        ))

        # I clicked on refund button.
        account_invoice_refund_2.with_context(context).invoice_refund()
        invoice_2.refund_invoice_ids and invoice_2.refund_invoice_ids[0].action_invoice_open()

        self.assertEqual(sum(order.order_line.mapped('amt_to_invoice')), 0.0, 'Sale: the Amount To Invoice for the sale order should be 0.0.')
        self.assertEqual(sum(order.order_line.mapped('amt_invoiced')), 0.0, 'Sale: the Amount Invoiced for the sale order should be 0.0.')

    def test_amount_delivered_and_ordered_qty(self):
        """ Testing amount to invoice and amount to be invoiced, with different invoice policy and cancelling SO """
        # disable mail feature to speed test
        context_no_mail = {
            'tracking_disable': True,
            'mail_notrack': True,
            'mail_create_nolog': True,
        }

        # create products and partner
        Product = self.env['product.product'].with_context(context_no_mail)
        product_order = Product.create({
            'name': "Service Ordered",
            'standard_price': 10,
            'list_price': 20,
            'type': 'service',
            'invoice_policy': 'order',
            'default_code': 'SERV-ORDERED1',
            'taxes_id': False, # force no tax
        })
        product_deli = Product.create({
            'name': 'iMac',
            'standard_price': 400,
            'list_price': 500,
            'type': 'consu',
            'invoice_policy': 'delivery',
            'default_code': 'E-COM09',
            'taxes_id': False, # force no tax
        })

        partner = self.env.ref('base.res_partner_1')
        partner.property_account_receivable_id = self.env['account.account'].search([('user_type_id', '=', self.env.ref('account.data_account_type_revenue').id)], limit=1)

        # create Sales order, with 2 lines: one delivered, one ordered
        order = self.env['sale.order'].with_context(context_no_mail).create({
            'partner_id': partner.id,
            'partner_invoice_id': partner.id,
            'partner_shipping_id': partner.id,
            'pricelist_id': self.env.ref('product.list0').id,
        })
        sale_line_ord = self.env['sale.order.line'].with_context(context_no_mail).create({
            'order_id': order.id,
            'name': product_order.name,
            'product_id': product_order.id,
            'product_uom_qty': 2,
            'qty_delivered': 0,
            'product_uom': product_order.uom_id.id,
            'price_unit': 20
        })
        sale_line_deli = self.env['sale.order.line'].with_context(context_no_mail).create({
            'order_id': order.id,
            'name': product_deli.name,
            'product_id': product_deli.id,
            'product_uom_qty': 2,
            'qty_delivered': 0,
            'product_uom': product_deli.uom_id.id,
            'price_unit': 500
        })

        self.assertEqual(sale_line_deli.amt_to_invoice, 0.0, 'Amount to invoice for delivered qty SO line should zero, since its state is draft')
        self.assertEqual(sale_line_deli.amt_invoiced, 0.0, 'Amount invoiced for delivered qty SO line should zero, since its state is draft, and there is no invoice at this moment')
        self.assertEqual(sale_line_ord.amt_to_invoice, 0.0, 'Amount to invoice for ordered qty SO line should zero, since its state is draft')
        self.assertEqual(sale_line_ord.amt_invoiced, 0.0, 'Amount invoiced for ordered qty SO line should zero, since its state is draft, and there is no invoice at this moment')

        # confirm SO
        order.action_confirm()

        self.assertEqual(sale_line_deli.amt_to_invoice, 0.0, 'Amount to invoice for delivered SO line is still zero, since its delivered quantity is zero')
        self.assertEqual(sale_line_deli.amt_invoiced, 0.0, 'Amount invoiced for delivered SO line is still zero, since its delivered quantity is zero, and there is no invoice at this moment')
        self.assertEqual(sale_line_ord.amt_to_invoice, 40.0, 'Amount to invoice for ordered SO line should be 40, even if there is no invoice')
        self.assertEqual(sale_line_ord.amt_invoiced, 0.0, 'Amount invoiced for ordered SO line should zero, there is no invoice at this moment')

        # create invoice for delivered product
        invoice_context = {"active_model": 'sale.order', "active_ids": [order.id], "active_id": order.id}
        payment = self.env['sale.advance.payment.inv'].with_context(context_no_mail).create({
            'advance_payment_method': 'delivered',
        })
        payment.with_context(invoice_context).create_invoices()
        invoice_1 = order.invoice_ids[0]

        self.assertEqual(sale_line_deli.amt_to_invoice, 0.0, 'Amount to invoice for delivered SO line is still zero, since its delivered quantity (on SO line) is zero')
        self.assertEqual(sale_line_deli.amt_invoiced, 0.0, 'Amount invoiced for delivered SO line is still zero, since its delivered quantity (on SO line) is zero, and there is no invoice at this moment')
        self.assertEqual(sale_line_ord.amt_to_invoice, 40.0, 'Amount to invoice for ordered SO line should be 40, since there is a draft invoice')
        self.assertEqual(sale_line_ord.amt_invoiced, 0.0, 'Amount invoiced for ordered SO line should zero, there is no validated invoice at this moment')

        # validate invoice
        invoice_1.action_invoice_open()

        self.assertEqual(sale_line_deli.amt_to_invoice, 0.0, 'Amount to invoice for delivered SO line is still zero, since its delivered quantity (on SO line) is zero')
        self.assertEqual(sale_line_deli.amt_invoiced, 0.0, 'Amount invoiced for delivered SO line is still zero, since its delivered quantity (on SO line) is zero, and there is no invoice at this moment')
        self.assertEqual(sale_line_ord.amt_to_invoice, 0.0, 'Amount to invoice for ordered SO line is zero, since the invoice is validated')
        self.assertEqual(sale_line_ord.amt_invoiced, 40.0, 'Amount invoiced for ordered SO line should 40, there is a validated invoice at this moment')

        # deliver 2 unit of product_deli
        sale_line_deli.write({'qty_delivered': 2})

        self.assertEqual(sale_line_deli.amt_to_invoice, 1000.0, 'Amount to invoice for delivered SO line is now 1000, since its delivered quantity (on SO line) is 2 (unit price = 500)')
        self.assertEqual(sale_line_deli.amt_invoiced, 0.0, 'Amount invoiced for delivered SO line is still zero, since there is no invoice at this moment for this product')
        self.assertEqual(sale_line_ord.amt_to_invoice, 0.0, 'Amount to invoice for ordered SO line is zero, since the invoice is validated')
        self.assertEqual(sale_line_ord.amt_invoiced, 40.0, 'Amount invoiced for ordered SO line should 40, there is a validated invoice at this moment')

        # create second invoice and validate it
        payment = self.env['sale.advance.payment.inv'].with_context(context_no_mail).create({
            'advance_payment_method': 'delivered',
        })
        payment.with_context(invoice_context).create_invoices()
        invoice_2 = order.invoice_ids.sorted(key='id')[1]
        invoice_2.action_invoice_open()

        self.assertEqual(sale_line_deli.amt_to_invoice, 0.0, 'Amount to invoice for delivered SO line is 0, since this is all invoiced')
        self.assertEqual(sale_line_deli.amt_invoiced, 1000.0, 'Amount invoiced for delivered SO line is now 1000, since the invoice for this product is validated')
        self.assertEqual(sale_line_ord.amt_to_invoice, 0.0, 'Amount to invoice for ordered SO line is zero, since the invoice is validated')
        self.assertEqual(sale_line_ord.amt_invoiced, 40.0, 'Amount invoiced for ordered SO line should 40, there is a validated invoice at this moment')

        # deliver 1 more unit of product_deli
        sale_line_deli.write({'qty_delivered': sale_line_deli.qty_delivered+1})

        self.assertEqual(sale_line_deli.amt_to_invoice, 500.0, 'Amount to invoice for delivered SO line is now 500, since we got a uninvoiced unit')
        self.assertEqual(sale_line_deli.amt_invoiced, 1000.0, 'Amount invoiced for delivered SO line is still 1000, even the delivered qty change')
        self.assertEqual(sale_line_ord.amt_to_invoice, 0.0, 'Amount to invoice for ordered SO line is zero, since the invoice is validated')
        self.assertEqual(sale_line_ord.amt_invoiced, 40.0, 'Amount invoiced for ordered SO line should 40, there is a validated invoice at this moment')

        # create third invoice
        payment = self.env['sale.advance.payment.inv'].with_context(context_no_mail).create({
            'advance_payment_method': 'delivered',
        })
        payment.with_context(invoice_context, open_invoices=True).create_invoices()
        invoice_3 = order.invoice_ids.sorted(key='id')[2]

        self.assertEqual(sale_line_deli.amt_to_invoice, 500.0, 'Amount to invoice for delivered SO line is now 500, since we got a uninvoiced unit')
        self.assertEqual(sale_line_deli.amt_invoiced, 1000.0, 'Amount invoiced for delivered SO line is still 1000')
        self.assertEqual(sale_line_ord.amt_to_invoice, 0.0, 'Amount to invoice for ordered SO line is zero, since the invoice is validated')
        self.assertEqual(sale_line_ord.amt_invoiced, 40.0, 'Amount invoiced for ordered SO line should 40, there is a validated invoice at this moment')

        # cancel order
        order.action_cancel()

        self.assertEqual(sale_line_deli.amt_to_invoice, 0.0, 'Amount to invoice for delivered SO line is now 0, since SO is cancel')
        self.assertEqual(sale_line_deli.amt_invoiced, 1000.0, 'Amount invoiced for delivered SO line is still 1000, even if the SO is cancelled')
        self.assertEqual(sale_line_ord.amt_to_invoice, 0.0, 'Amount to invoice for ordered SO line is zero, since the invoice is validated')
        self.assertEqual(sale_line_ord.amt_invoiced, 40.0, 'Amount invoiced for ordered SO line should 40, there is a validated invoice at this moment')

        # change the unit price on 3rd invoice
        invoice_3.invoice_line_ids.write({'price_unit': 300})

        self.assertEqual(sale_line_deli.amt_to_invoice, 0.0, 'Amount to invoice for delivered SO line is now 0: nothing should change as the invoice is in draft state')
        self.assertEqual(sale_line_deli.amt_invoiced, 1000.0, 'Amount invoiced for delivered SO line is still 1000, even if we change price of unvalidated invoice')
        self.assertEqual(sale_line_ord.amt_to_invoice, 0.0, 'Amount to invoice for ordered SO line is zero, since the invoice is validated')
        self.assertEqual(sale_line_ord.amt_invoiced, 40.0, 'Amount invoiced for ordered SO line should 40, there is a validated invoice at this moment')

        # validate third invoice
        invoice_3.action_invoice_open()

        self.assertEqual(sale_line_deli.amt_to_invoice, 0.0, 'Amount to invoice for delivered SO line is now 0, since SO is cancel')
        self.assertEqual(sale_line_deli.amt_invoiced, 1300.0, 'Amount invoiced for delivered SO line is incremented, since the 3rd invoice for this product is validated')
        self.assertEqual(sale_line_ord.amt_to_invoice, 0.0, 'Amount to invoice for ordered SO line is zero, since the invoice is validated')
        self.assertEqual(sale_line_ord.amt_invoiced, 40.0, 'Amount invoiced for ordered SO line should 40, there is a validated invoice at this moment')
