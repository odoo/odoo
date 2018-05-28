# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tools import pycompat
from .test_sale_common import TestCommonSaleNoChart


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
            'default_journal_id': cls.journal_sale
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
            'amount': 100,
            'deposit_account_id': self.account_income.id
        })
        payment.create_invoices()

        self.assertEquals(len(self.sale_order.invoice_ids), 1, 'Invoice should be created for the SO')
        downpayment_line = self.sale_order.order_line.filtered(lambda l: l.is_downpayment)
        self.assertEquals(len(downpayment_line), 1, 'SO line downpayment should be created on SO')

        # Update delivered quantity of SO lines
        self.sol_serv_deliver.write({'qty_delivered': 4.0})
        self.sol_prod_deliver.write({'qty_delivered': 2.0})

        # Let's do an invoice with refunds
        payment = self.env['sale.advance.payment.inv'].with_context(self.context).create({
            'advance_payment_method': 'all',
            'deposit_account_id': self.account_income.id
        })
        payment.create_invoices()

        self.assertEquals(len(self.sale_order.invoice_ids), 2, 'Invoice should be created for the SO')

        invoice = self.sale_order.invoice_ids[0]
        self.assertEquals(len(invoice.invoice_line_ids), len(self.sale_order.order_line), 'All lines should be invoiced')
        self.assertEquals(invoice.amount_total, self.sale_order.amount_total - downpayment_line.price_unit, 'Downpayment should be applied')

    def test_invoice_with_discount(self):
        """ Test invoice with a discount and check discount applied on both SO lines and an invoice lines """
        # Update discount and delivered quantity on SO lines
        self.sol_prod_order.write({'discount': 20.0})
        self.sol_serv_deliver.write({'discount': 20.0, 'qty_delivered': 4.0})
        self.sol_serv_order.write({'discount': -10.0})
        self.sol_prod_deliver.write({'qty_delivered': 2.0})

        for line in self.sale_order.order_line.filtered(lambda l: l.discount):
            product_price = line.price_unit * line.product_uom_qty
            self.assertEquals(line.discount, (product_price - line.price_subtotal) / product_price * 100, 'Discount should be applied on order line')

        self.sale_order.action_confirm()

        # Let's do an invoice with invoiceable lines
        payment = self.env['sale.advance.payment.inv'].with_context(self.context).create({
            'advance_payment_method': 'delivered'
        })
        payment.create_invoices()
        invoice = self.sale_order.invoice_ids[0]
        invoice.action_invoice_open()

        # Check discount appeared on both SO lines and invoice lines
        for line, inv_line in pycompat.izip(self.sale_order.order_line, invoice.invoice_line_ids):
            self.assertEquals(line.discount, inv_line.discount, 'Discount on lines of order and invoice should be same')

    def test_invoice_refund(self):
        """ Test invoice with a refund and check customer invoices credit note is created from respective invoice """
        # Confirm the SO
        self.sale_order.action_confirm()
        # Take only invoicable line
        order_line = self.sale_order.order_line.filtered(lambda l: l.product_id.invoice_policy == 'order')
        # Check ordered quantity, quantity to invoice and invoiced quantity of SO lines
        for line in order_line:
            self.assertEquals(line.qty_to_invoice, line.product_uom_qty, 'Quantity to invoice should be same as ordered quantity')
            self.assertEquals(line.qty_invoiced, 0.0, 'Invoiced quantity should be zero as no any invoice created for SO')

        # Let's do an invoice with invoiceable lines
        payment = self.env['sale.advance.payment.inv'].with_context(self.context).create({
            'advance_payment_method': 'delivered'
        })
        payment.create_invoices()

        invoice = self.sale_order.invoice_ids[0]

        # Update quantity of an invoice lines
        invoice.invoice_line_ids[0].write({'quantity': 3.0})
        invoice.invoice_line_ids[1].write({'quantity': 2.0})
        invoice.action_invoice_open()

        # Check quantity to invoice on SO lines
        for line in order_line:
            self.assertEquals(line.qty_to_invoice, line.product_uom_qty - line.qty_invoiced, 'Quantity to invoice should be a difference between ordered quantity and invoiced quantity')

        # Make a credit note
        credit_note = self.env['account.invoice.refund'].with_context({'active_ids': [invoice.id], 'active_id': invoice.id}).create({
            'filter_refund': 'refund',
            'description': 'test'
        })
        credit_note.invoice_refund()
        invoice_credit_note = self.sale_order.invoice_ids[1]

        # Check invoice's type and number
        self.assertEquals(invoice_credit_note.type, 'out_refund', 'Invoice type should be a customer credit note')
        self.assertEquals(invoice.number, invoice_credit_note.origin, 'Customer invoices credit note should be created from respective invoice')
