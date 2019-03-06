# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tools import pycompat, float_is_zero
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

        # lines are in draft
        for line in self.sale_order.order_line:
            self.assertTrue(float_is_zero(line.untaxed_amount_to_invoice, precision_digits=2), "The amount to invoice should be zero, as the line is in draf state")
            self.assertTrue(float_is_zero(line.untaxed_amount_invoiced, precision_digits=2), "The invoiced amount should be zero, as the line is in draft state")

        self.sale_order.action_confirm()

        for line in self.sale_order.order_line:
            self.assertTrue(float_is_zero(line.untaxed_amount_invoiced, precision_digits=2), "The invoiced amount should be zero, as the line is in draft state")

        self.assertEquals(self.sol_serv_order.untaxed_amount_to_invoice, 297, "The untaxed amount to invoice is wrong")
        self.assertEquals(self.sol_serv_deliver.untaxed_amount_to_invoice, self.sol_serv_deliver.qty_delivered * self.sol_serv_deliver.price_reduce, "The untaxed amount to invoice should be qty deli * price reduce, so 4 * (180 - 36)")
        self.assertEquals(self.sol_prod_deliver.untaxed_amount_to_invoice, 140, "The untaxed amount to invoice should be qty deli * price reduce, so 4 * (180 - 36)")

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
        # lines are in draft
        for line in self.sale_order.order_line:
            self.assertTrue(float_is_zero(line.untaxed_amount_to_invoice, precision_digits=2), "The amount to invoice should be zero, as the line is in draf state")
            self.assertTrue(float_is_zero(line.untaxed_amount_invoiced, precision_digits=2), "The invoiced amount should be zero, as the line is in draft state")

        # Confirm the SO
        self.sale_order.action_confirm()

        # Check ordered quantity, quantity to invoice and invoiced quantity of SO lines
        for line in self.sale_order.order_line:
            if line.product_id.invoice_policy == 'delivery':
                self.assertEquals(line.qty_to_invoice, 0.0, 'Quantity to invoice should be same as ordered quantity')
                self.assertEquals(line.qty_invoiced, 0.0, 'Invoiced quantity should be zero as no any invoice created for SO')
                self.assertEquals(line.untaxed_amount_to_invoice, 0.0, "The amount to invoice should be zero, as the line based on delivered quantity")
                self.assertEquals(line.untaxed_amount_invoiced, 0.0, "The invoiced amount should be zero, as the line based on delivered quantity")
            else:
                self.assertEquals(line.qty_to_invoice, line.product_uom_qty, 'Quantity to invoice should be same as ordered quantity')
                self.assertEquals(line.qty_invoiced, 0.0, 'Invoiced quantity should be zero as no any invoice created for SO')
                self.assertEquals(line.untaxed_amount_to_invoice, line.product_uom_qty * line.price_unit, "The amount to invoice should the total of the line, as the line is confirmed")
                self.assertEquals(line.untaxed_amount_invoiced, 0.0, "The invoiced amount should be zero, as the line is confirmed")

        # Let's do an invoice with invoiceable lines
        payment = self.env['sale.advance.payment.inv'].with_context(self.context).create({
            'advance_payment_method': 'delivered'
        })
        payment.create_invoices()

        invoice = self.sale_order.invoice_ids[0]

        # Update quantity of an invoice lines
        invoice.invoice_line_ids[0].write({'quantity': 3.0})  # product ordered: from 5 to 3
        invoice.invoice_line_ids[1].write({'quantity': 2.0})  # service ordered: from 3 to 2

        # amount to invoice / invoiced should not have changed (amounts take only confirmed invoice into account)
        for line in self.sale_order.order_line:
            if line.product_id.invoice_policy == 'delivery':
                self.assertEquals(line.qty_to_invoice, 0.0, "Quantity to invoice should be zero")
                self.assertEquals(line.qty_invoiced, 0.0, "Invoiced quantity should be zero as delivered lines are not delivered yet")
                self.assertEquals(line.untaxed_amount_to_invoice, 0.0, "The amount to invoice should be zero, as the line based on delivered quantity (no confirmed invoice)")
                self.assertEquals(line.untaxed_amount_invoiced, 0.0, "The invoiced amount should be zero, as no invoice are validated for now")
            else:
                if line == self.sol_prod_order:
                    self.assertEquals(self.sol_prod_order.qty_to_invoice, 2.0, "Changing the quantity on draft invoice update the qty to invoice on SO lines")
                    self.assertEquals(self.sol_prod_order.qty_invoiced, 3.0, "Changing the quantity on draft invoice update the invoiced qty on SO lines")
                else:
                    self.assertEquals(self.sol_serv_order.qty_to_invoice, 1.0, "Changing the quantity on draft invoice update the qty to invoice on SO lines")
                    self.assertEquals(self.sol_serv_order.qty_invoiced, 2.0, "Changing the quantity on draft invoice update the invoiced qty on SO lines")
                self.assertEquals(line.untaxed_amount_to_invoice, line.product_uom_qty * line.price_unit, "The amount to invoice should the total of the line, as the line is confirmed (no confirmed invoice)")
                self.assertEquals(line.untaxed_amount_invoiced, 0.0, "The invoiced amount should be zero, as no invoice are validated for now")

        invoice.action_invoice_open()

        # Check quantity to invoice on SO lines
        for line in self.sale_order.order_line:
            if line.product_id.invoice_policy == 'delivery':
                self.assertEquals(line.qty_to_invoice, 0.0, "Quantity to invoice should be same as ordered quantity")
                self.assertEquals(line.qty_invoiced, 0.0, "Invoiced quantity should be zero as no any invoice created for SO")
                self.assertEquals(line.untaxed_amount_to_invoice, 0.0, "The amount to invoice should be zero, as the line based on delivered quantity")
                self.assertEquals(line.untaxed_amount_invoiced, 0.0, "The invoiced amount should be zero, as the line based on delivered quantity")
            else:
                if line == self.sol_prod_order:
                    self.assertEquals(line.qty_to_invoice, 2.0, "The ordered sale line are totally invoiced (qty to invoice is zero)")
                    self.assertEquals(line.qty_invoiced, 3.0, "The ordered (prod) sale line are totally invoiced (qty invoiced come from the invoice lines)")
                else:
                    self.assertEquals(line.qty_to_invoice, 1.0, "The ordered sale line are totally invoiced (qty to invoice is zero)")
                    self.assertEquals(line.qty_invoiced, 2.0, "The ordered (serv) sale line are totally invoiced (qty invoiced = the invoice lines)")
                self.assertEquals(line.untaxed_amount_to_invoice, line.price_unit * line.qty_to_invoice, "Amount to invoice is now set as qty to invoice * unit price since no price change on invoice, for ordered products")
                self.assertEquals(line.untaxed_amount_invoiced, line.price_unit * line.qty_invoiced, "Amount invoiced is now set as qty invoiced * unit price since no price change on invoice, for ordered products")

        # Make a credit note
        credit_note_wizard = self.env['account.invoice.refund'].with_context({'active_ids': [invoice.id], 'active_id': invoice.id}).create({
            'filter_refund': 'modify',  # this is the only mode for which the SO line is linked to the refund (https://github.com/odoo/odoo/commit/e680f29560ac20133c7af0c6364c6ef494662eac)
            'description': 'reason test',
        })
        credit_note_wizard.invoice_refund()
        invoice_2 = self.sale_order.invoice_ids.sorted(key=lambda inv: inv.id, reverse=False)[-1]  # the first invoice, its refund, and the new invoice

        # Check invoice's type and number
        self.assertEquals(invoice_2.type, 'out_invoice', 'The last created invoiced should be a customer invoice')
        self.assertEquals(invoice_2.state, 'draft', 'Last Customer invoices should be in draft')

        # At this time, the invoice 1 and its refund are confirmed, so the amounts invoiced are zero. The third invoice
        # (2nd customer inv) is in draft state.
        for line in self.sale_order.order_line:
            if line.product_id.invoice_policy == 'delivery':
                self.assertEquals(line.qty_to_invoice, 0.0, "Quantity to invoice should be same as ordered quantity")
                self.assertEquals(line.qty_invoiced, 0.0, "Invoiced quantity should be zero as no any invoice created for SO")
                self.assertEquals(line.untaxed_amount_to_invoice, 0.0, "The amount to invoice should be zero, as the line based on delivered quantity")
                self.assertEquals(line.untaxed_amount_invoiced, 0.0, "The invoiced amount should be zero, as the line based on delivered quantity")
            else:
                if line == self.sol_prod_order:
                    self.assertEquals(line.qty_to_invoice, 2.0, "The qty to invoice does not change when confirming the new invoice (2)")
                    self.assertEquals(line.qty_invoiced, 3.0, "The ordered (prod) sale line does not change on invoice 2 confirmation")
                    self.assertEquals(line.untaxed_amount_to_invoice, line.price_unit * 5, "Amount to invoice is now set as qty to invoice * unit price since no price change on invoice, for ordered products")
                    self.assertEquals(line.untaxed_amount_invoiced, 0.0, "Amount invoiced is zero as the invoice 1 and its refund are reconcilied")
                else:
                    self.assertEquals(line.qty_to_invoice, 1.0, "The qty to invoice does not change when confirming the new invoice (2)")
                    self.assertEquals(line.qty_invoiced, 2.0, "The ordered (serv) sale line does not change on invoice 2 confirmation")
                    self.assertEquals(line.untaxed_amount_to_invoice, line.price_unit * 3, "Amount to invoice is now set as unit price * ordered qty - refund qty) even if the ")
                    self.assertEquals(line.untaxed_amount_invoiced, 0.0, "Amount invoiced is zero as the invoice 1 and its refund are reconcilied")

        # Change unit of ordered product on refund lines
        invoice_2.invoice_line_ids.filtered(lambda invl: invl.product_id == self.sol_prod_order.product_id).write({'price_unit': 100})
        invoice_2.invoice_line_ids.filtered(lambda invl: invl.product_id == self.sol_serv_order.product_id).write({'price_unit': 50})

        # Validate the refund
        invoice_2.action_invoice_open()

        for line in self.sale_order.order_line:
            if line.product_id.invoice_policy == 'delivery':
                self.assertEquals(line.qty_to_invoice, 0.0, "Quantity to invoice should be same as ordered quantity")
                self.assertEquals(line.qty_invoiced, 0.0, "Invoiced quantity should be zero as no any invoice created for SO")
                self.assertEquals(line.untaxed_amount_to_invoice, 0.0, "The amount to invoice should be zero, as the line based on delivered quantity")
                self.assertEquals(line.untaxed_amount_invoiced, 0.0, "The invoiced amount should be zero, as the line based on delivered quantity")
            else:
                if line == self.sol_prod_order:
                    self.assertEquals(line.qty_to_invoice, 2.0, "The qty to invoice does not change when confirming the new invoice (2)")
                    self.assertEquals(line.qty_invoiced, 3.0, "The ordered sale line are totally invoiced (qty invoiced = ordered qty)")
                    self.assertEquals(line.untaxed_amount_to_invoice, 1100.0, "")
                    self.assertEquals(line.untaxed_amount_invoiced, 300.0, "")
                else:
                    self.assertEquals(line.qty_to_invoice, 1.0, "The qty to invoice does not change when confirming the new invoice (2)")
                    self.assertEquals(line.qty_invoiced, 2.0, "The ordered sale line are totally invoiced (qty invoiced = ordered qty)")
                    self.assertEquals(line.untaxed_amount_to_invoice, 170.0, "")
                    self.assertEquals(line.untaxed_amount_invoiced, 100.0, "")
