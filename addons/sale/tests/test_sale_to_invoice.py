# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tools import float_is_zero
from .test_sale_common import TestCommonSaleNoChart
from odoo.tests import Form


class TestSaleToInvoice(TestCommonSaleNoChart):

    @classmethod
    def setUpClass(cls):
        super(TestSaleToInvoice, cls).setUpClass()

        cls.setUpClassicProducts()
        cls.setUpAdditionalAccounts()
        cls.setUpAccountJournal()

        # Create the SO with four order lines
        cls.sale_order = cls.env['sale.order'].with_context(tracking_disable=True).create({
            'partner_id': cls.partner_customer_usd.id,
            'partner_invoice_id': cls.partner_customer_usd.id,
            'partner_shipping_id': cls.partner_customer_usd.id,
            'pricelist_id': cls.pricelist_usd.id,
        })
        SaleOrderLine = cls.env['sale.order.line'].with_context(tracking_disable=True)
        cls.sol_prod_order = SaleOrderLine.create({
            'name': cls.product_order.name,
            'product_id': cls.product_order.id,
            'product_uom_qty': 5,
            'product_uom': cls.product_order.uom_id.id,
            'price_unit': cls.product_order.list_price,
            'order_id': cls.sale_order.id,
            'tax_id': False,
        })
        cls.sol_serv_deliver = SaleOrderLine.create({
            'name': cls.service_deliver.name,
            'product_id': cls.service_deliver.id,
            'product_uom_qty': 4,
            'product_uom': cls.service_deliver.uom_id.id,
            'price_unit': cls.service_deliver.list_price,
            'order_id': cls.sale_order.id,
            'tax_id': False,
        })
        cls.sol_serv_order = SaleOrderLine.create({
            'name': cls.service_order.name,
            'product_id': cls.service_order.id,
            'product_uom_qty': 3,
            'product_uom': cls.service_order.uom_id.id,
            'price_unit': cls.service_order.list_price,
            'order_id': cls.sale_order.id,
            'tax_id': False,
        })
        cls.sol_prod_deliver = SaleOrderLine.create({
            'name': cls.product_deliver.name,
            'product_id': cls.product_deliver.id,
            'product_uom_qty': 2,
            'product_uom': cls.product_deliver.uom_id.id,
            'price_unit': cls.product_deliver.list_price,
            'order_id': cls.sale_order.id,
            'tax_id': False,
        })

        # Context
        cls.context = {
            'active_model': 'sale.order',
            'active_ids': [cls.sale_order.id],
            'active_id': cls.sale_order.id,
            'default_journal_id': cls.journal_sale.id,
        }

    def test_downpayment(self):
        """ Test invoice with a way of downpayment and check downpayment's SO line is created
            and also check a total amount of invoice is equal to a respective sale order's total amount
        """
        # Confirm the SO
        self.sale_order.action_confirm()
        # Let's do an invoice for a deposit of 100
        payment = self.env['sale.advance.payment.inv'].with_context(self.context).create({
            'advance_payment_method': 'fixed',
            'fixed_amount': 100,
            'deposit_account_id': self.account_income.id
        })
        payment.create_invoices()

        self.assertEqual(len(self.sale_order.invoice_ids), 1, 'Invoice should be created for the SO')
        downpayment_line = self.sale_order.order_line.filtered(lambda l: l.is_downpayment)
        self.assertEqual(len(downpayment_line), 1, 'SO line downpayment should be created on SO')

        # Update delivered quantity of SO lines
        self.sol_serv_deliver.write({'qty_delivered': 4.0})
        self.sol_prod_deliver.write({'qty_delivered': 2.0})

        # Let's do an invoice with refunds
        payment = self.env['sale.advance.payment.inv'].with_context(self.context).create({
            'deposit_account_id': self.account_income.id
        })
        payment.create_invoices()

        self.assertEqual(len(self.sale_order.invoice_ids), 2, 'Invoice should be created for the SO')

        invoice = self.sale_order.invoice_ids.sorted()[-1]
        self.assertEqual(len(invoice.invoice_line_ids), len(self.sale_order.order_line), 'All lines should be invoiced')
        self.assertEqual(invoice.amount_total, self.sale_order.amount_total - downpayment_line.price_unit, 'Downpayment should be applied')

    def test_invoice_with_discount(self):
        """ Test invoice with a discount and check discount applied on both SO lines and an invoice lines """
        # Update discount and delivered quantity on SO lines
        self.sol_prod_order.write({'discount': 20.0})
        self.sol_serv_deliver.write({'discount': 20.0, 'qty_delivered': 4.0})
        self.sol_serv_order.write({'discount': -10.0})
        self.sol_prod_deliver.write({'qty_delivered': 2.0})

        for line in self.sale_order.order_line.filtered(lambda l: l.discount):
            product_price = line.price_unit * line.product_uom_qty
            self.assertEqual(line.discount, (product_price - line.price_subtotal) / product_price * 100, 'Discount should be applied on order line')

        # lines are in draft
        for line in self.sale_order.order_line:
            self.assertTrue(float_is_zero(line.untaxed_amount_to_invoice, precision_digits=2), "The amount to invoice should be zero, as the line is in draf state")
            self.assertTrue(float_is_zero(line.untaxed_amount_invoiced, precision_digits=2), "The invoiced amount should be zero, as the line is in draft state")

        self.sale_order.action_confirm()

        for line in self.sale_order.order_line:
            self.assertTrue(float_is_zero(line.untaxed_amount_invoiced, precision_digits=2), "The invoiced amount should be zero, as the line is in draft state")

        self.assertEqual(self.sol_serv_order.untaxed_amount_to_invoice, 297, "The untaxed amount to invoice is wrong")
        self.assertEqual(self.sol_serv_deliver.untaxed_amount_to_invoice, self.sol_serv_deliver.qty_delivered * self.sol_serv_deliver.price_reduce, "The untaxed amount to invoice should be qty deli * price reduce, so 4 * (180 - 36)")
        self.assertEqual(self.sol_prod_deliver.untaxed_amount_to_invoice, 140, "The untaxed amount to invoice should be qty deli * price reduce, so 4 * (180 - 36)")

        # Let's do an invoice with invoiceable lines
        payment = self.env['sale.advance.payment.inv'].with_context(self.context).create({
            'advance_payment_method': 'delivered'
        })
        payment.create_invoices()
        invoice = self.sale_order.invoice_ids[0]
        invoice.post()

        # Check discount appeared on both SO lines and invoice lines
        for line, inv_line in zip(self.sale_order.order_line, invoice.invoice_line_ids):
            self.assertEqual(line.discount, inv_line.discount, 'Discount on lines of order and invoice should be same')

    def test_invoice(self):
        """ Test create and invoice from the SO, and check qty invoice/to invoice, and the related amounts """
        # lines are in draft
        for line in self.sale_order.order_line:
            self.assertTrue(float_is_zero(line.untaxed_amount_to_invoice, precision_digits=2), "The amount to invoice should be zero, as the line is in draf state")
            self.assertTrue(float_is_zero(line.untaxed_amount_invoiced, precision_digits=2), "The invoiced amount should be zero, as the line is in draft state")

        # Confirm the SO
        self.sale_order.action_confirm()

        # Check ordered quantity, quantity to invoice and invoiced quantity of SO lines
        for line in self.sale_order.order_line:
            if line.product_id.invoice_policy == 'delivery':
                self.assertEqual(line.qty_to_invoice, 0.0, 'Quantity to invoice should be same as ordered quantity')
                self.assertEqual(line.qty_invoiced, 0.0, 'Invoiced quantity should be zero as no any invoice created for SO')
                self.assertEqual(line.untaxed_amount_to_invoice, 0.0, "The amount to invoice should be zero, as the line based on delivered quantity")
                self.assertEqual(line.untaxed_amount_invoiced, 0.0, "The invoiced amount should be zero, as the line based on delivered quantity")
            else:
                self.assertEqual(line.qty_to_invoice, line.product_uom_qty, 'Quantity to invoice should be same as ordered quantity')
                self.assertEqual(line.qty_invoiced, 0.0, 'Invoiced quantity should be zero as no any invoice created for SO')
                self.assertEqual(line.untaxed_amount_to_invoice, line.product_uom_qty * line.price_unit, "The amount to invoice should the total of the line, as the line is confirmed")
                self.assertEqual(line.untaxed_amount_invoiced, 0.0, "The invoiced amount should be zero, as the line is confirmed")

        # Let's do an invoice with invoiceable lines
        payment = self.env['sale.advance.payment.inv'].with_context(self.context).create({
            'advance_payment_method': 'delivered'
        })
        payment.create_invoices()

        invoice = self.sale_order.invoice_ids[0]

        # Update quantity of an invoice lines
        move_form = Form(invoice)
        with move_form.invoice_line_ids.edit(0) as line_form:
            line_form.quantity = 3.0
        with move_form.invoice_line_ids.edit(1) as line_form:
            line_form.quantity = 2.0
        invoice = move_form.save()

        # amount to invoice / invoiced should not have changed (amounts take only confirmed invoice into account)
        for line in self.sale_order.order_line:
            if line.product_id.invoice_policy == 'delivery':
                self.assertEqual(line.qty_to_invoice, 0.0, "Quantity to invoice should be zero")
                self.assertEqual(line.qty_invoiced, 0.0, "Invoiced quantity should be zero as delivered lines are not delivered yet")
                self.assertEqual(line.untaxed_amount_to_invoice, 0.0, "The amount to invoice should be zero, as the line based on delivered quantity (no confirmed invoice)")
                self.assertEqual(line.untaxed_amount_invoiced, 0.0, "The invoiced amount should be zero, as no invoice are validated for now")
            else:
                if line == self.sol_prod_order:
                    self.assertEqual(self.sol_prod_order.qty_to_invoice, 2.0, "Changing the quantity on draft invoice update the qty to invoice on SO lines")
                    self.assertEqual(self.sol_prod_order.qty_invoiced, 3.0, "Changing the quantity on draft invoice update the invoiced qty on SO lines")
                else:
                    self.assertEqual(self.sol_serv_order.qty_to_invoice, 1.0, "Changing the quantity on draft invoice update the qty to invoice on SO lines")
                    self.assertEqual(self.sol_serv_order.qty_invoiced, 2.0, "Changing the quantity on draft invoice update the invoiced qty on SO lines")
                self.assertEqual(line.untaxed_amount_to_invoice, line.product_uom_qty * line.price_unit, "The amount to invoice should the total of the line, as the line is confirmed (no confirmed invoice)")
                self.assertEqual(line.untaxed_amount_invoiced, 0.0, "The invoiced amount should be zero, as no invoice are validated for now")

        invoice.post()

        # Check quantity to invoice on SO lines
        for line in self.sale_order.order_line:
            if line.product_id.invoice_policy == 'delivery':
                self.assertEqual(line.qty_to_invoice, 0.0, "Quantity to invoice should be same as ordered quantity")
                self.assertEqual(line.qty_invoiced, 0.0, "Invoiced quantity should be zero as no any invoice created for SO")
                self.assertEqual(line.untaxed_amount_to_invoice, 0.0, "The amount to invoice should be zero, as the line based on delivered quantity")
                self.assertEqual(line.untaxed_amount_invoiced, 0.0, "The invoiced amount should be zero, as the line based on delivered quantity")
            else:
                if line == self.sol_prod_order:
                    self.assertEqual(line.qty_to_invoice, 2.0, "The ordered sale line are totally invoiced (qty to invoice is zero)")
                    self.assertEqual(line.qty_invoiced, 3.0, "The ordered (prod) sale line are totally invoiced (qty invoiced come from the invoice lines)")
                else:
                    self.assertEqual(line.qty_to_invoice, 1.0, "The ordered sale line are totally invoiced (qty to invoice is zero)")
                    self.assertEqual(line.qty_invoiced, 2.0, "The ordered (serv) sale line are totally invoiced (qty invoiced = the invoice lines)")
                self.assertEqual(line.untaxed_amount_to_invoice, line.price_unit * line.qty_to_invoice, "Amount to invoice is now set as qty to invoice * unit price since no price change on invoice, for ordered products")
                self.assertEqual(line.untaxed_amount_invoiced, line.price_unit * line.qty_invoiced, "Amount invoiced is now set as qty invoiced * unit price since no price change on invoice, for ordered products")
