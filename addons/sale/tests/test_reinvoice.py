# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.sale.tests.test_sale_common import TestCommonSaleNoChart
from odoo.tests import Form


class TestReInvoice(TestCommonSaleNoChart):

    @classmethod
    def setUpClass(cls):
        super(TestReInvoice, cls).setUpClass()

        cls.setUpExpenseProducts()
        cls.setUpAdditionalAccounts()
        cls.setUpAccountJournal()

        cls.analytic_account = cls.env['account.analytic.account'].create({
            'name': 'Test AA',
            'code': 'TESTSALE_REINVOICE',
            'company_id': cls.partner_customer_usd.company_id.id,
            'partner_id': cls.partner_customer_usd.id
        })

        cls.sale_order = cls.env['sale.order'].with_context(mail_notrack=True, mail_create_nolog=True).create({
            'partner_id': cls.partner_customer_usd.id,
            'partner_invoice_id': cls.partner_customer_usd.id,
            'partner_shipping_id': cls.partner_customer_usd.id,
            'analytic_account_id': cls.analytic_account.id,
        })

        cls.AccountMove = cls.env['account.move'].with_context(default_type='in_invoice', mail_notrack=True, mail_create_nolog=True)

    def test_at_cost(self):
        """ Test vendor bill at cost for product based on ordered and delivered quantities. """
        # create SO line and confirm SO (with only one line)
        sale_order_line1 = self.env['sale.order.line'].create({
            'name': self.product_ordered_cost.name,
            'product_id': self.product_ordered_cost.id,
            'product_uom_qty': 2,
            'qty_delivered': 1,
            'product_uom': self.product_ordered_cost.uom_id.id,
            'price_unit': self.product_ordered_cost.list_price,
            'order_id': self.sale_order.id,
        })
        sale_order_line1.product_id_change()
        sale_order_line2 = self.env['sale.order.line'].create({
            'name': self.product_deliver_cost.name,
            'product_id': self.product_deliver_cost.id,
            'product_uom_qty': 4,
            'qty_delivered': 1,
            'product_uom': self.product_deliver_cost.uom_id.id,
            'price_unit': self.product_deliver_cost.list_price,
            'order_id': self.sale_order.id,
        })
        sale_order_line2.product_id_change()

        self.sale_order.onchange_partner_id()
        self.sale_order._compute_tax_id()
        self.sale_order.action_confirm()

        # create invoice lines and validate it
        move_form = Form(self.AccountMove)
        move_form.partner_id = self.partner_customer_usd
        with move_form.line_ids.new() as line_form:
            line_form.product_id = self.product_ordered_cost
            line_form.quantity = 3.0
            line_form.analytic_account_id = self.analytic_account
        with move_form.line_ids.new() as line_form:
            line_form.product_id = self.product_deliver_cost
            line_form.quantity = 3.0
            line_form.analytic_account_id = self.analytic_account
        invoice_a = move_form.save()
        invoice_a.post()

        sale_order_line3 = self.sale_order.order_line.filtered(lambda sol: sol != sale_order_line1 and sol.product_id == self.product_ordered_cost)
        sale_order_line4 = self.sale_order.order_line.filtered(lambda sol: sol != sale_order_line2 and sol.product_id == self.product_deliver_cost)

        self.assertTrue(sale_order_line3, "A new sale line should have been created with ordered product")
        self.assertTrue(sale_order_line4, "A new sale line should have been created with delivered product")
        self.assertEquals(len(self.sale_order.order_line), 4, "There should be 4 lines on the SO (2 vendor bill lines created)")
        self.assertEquals(len(self.sale_order.order_line.filtered(lambda sol: sol.is_expense)), 2, "There should be 4 lines on the SO (2 vendor bill lines created)")

        self.assertEquals(sale_order_line1.qty_delivered, 1, "Exising SO line 1 should not be impacted by reinvoicing product at cost")
        self.assertEquals(sale_order_line2.qty_delivered, 1, "Exising SO line 2 should not be impacted by reinvoicing product at cost")

        self.assertEquals((sale_order_line3.price_unit, sale_order_line3.qty_delivered, sale_order_line3.product_uom_qty, sale_order_line3.qty_invoiced), (self.product_ordered_cost.standard_price, 3, 0, 0), 'Sale line is wrong after confirming vendor invoice')
        self.assertEquals((sale_order_line4.price_unit, sale_order_line4.qty_delivered, sale_order_line4.product_uom_qty, sale_order_line4.qty_invoiced), (self.product_deliver_cost.standard_price, 3, 0, 0), 'Sale line is wrong after confirming vendor invoice')

        self.assertEquals(sale_order_line3.qty_delivered_method, 'analytic', "Delivered quantity of 'expense' SO line should be computed by analytic amount")
        self.assertEquals(sale_order_line4.qty_delivered_method, 'analytic', "Delivered quantity of 'expense' SO line should be computed by analytic amount")

        # create second invoice lines and validate it
        move_form = Form(self.AccountMove)
        move_form.partner_id = self.partner_customer_usd
        with move_form.line_ids.new() as line_form:
            line_form.product_id = self.product_ordered_cost
            line_form.quantity = 2.0
            line_form.analytic_account_id = self.analytic_account
        with move_form.line_ids.new() as line_form:
            line_form.product_id = self.product_deliver_cost
            line_form.quantity = 2.0
            line_form.analytic_account_id = self.analytic_account
        invoice_b = move_form.save()
        invoice_b.post()

        sale_order_line5 = self.sale_order.order_line.filtered(lambda sol: sol != sale_order_line1 and sol != sale_order_line3 and sol.product_id == self.product_ordered_cost)
        sale_order_line6 = self.sale_order.order_line.filtered(lambda sol: sol != sale_order_line2 and sol != sale_order_line4 and sol.product_id == self.product_deliver_cost)

        self.assertTrue(sale_order_line5, "A new sale line should have been created with ordered product")
        self.assertTrue(sale_order_line6, "A new sale line should have been created with delivered product")

        self.assertEquals(len(self.sale_order.order_line), 6, "There should be still 4 lines on the SO, no new created")
        self.assertEquals(len(self.sale_order.order_line.filtered(lambda sol: sol.is_expense)), 4, "There should be still 2 expenses lines on the SO")

        self.assertEquals((sale_order_line5.price_unit, sale_order_line5.qty_delivered, sale_order_line5.product_uom_qty, sale_order_line5.qty_invoiced), (self.product_ordered_cost.standard_price, 2, 0, 0), 'Sale line 5 is wrong after confirming 2e vendor invoice')
        self.assertEquals((sale_order_line6.price_unit, sale_order_line6.qty_delivered, sale_order_line6.product_uom_qty, sale_order_line6.qty_invoiced), (self.product_deliver_cost.standard_price, 2, 0, 0), 'Sale line 6 is wrong after confirming 2e vendor invoice')

    def test_sales_price(self):
        """ Test invoicing vendor bill at sales price for products based on delivered and ordered quantities. Check no existing SO line is incremented, but when invoicing a
            second time, increment only the delivered so line.
        """
        # create SO line and confirm SO (with only one line)
        sale_order_line1 = self.env['sale.order.line'].create({
            'name': self.product_deliver_sales_price.name,
            'product_id': self.product_deliver_sales_price.id,
            'product_uom_qty': 2,
            'qty_delivered': 1,
            'product_uom': self.product_deliver_sales_price.uom_id.id,
            'price_unit': self.product_deliver_sales_price.list_price,
            'order_id': self.sale_order.id,
        })
        sale_order_line1.product_id_change()
        sale_order_line2 = self.env['sale.order.line'].create({
            'name': self.product_order_sales_price.name,
            'product_id': self.product_order_sales_price.id,
            'product_uom_qty': 3,
            'qty_delivered': 1,
            'product_uom': self.product_order_sales_price.uom_id.id,
            'price_unit': self.product_order_sales_price.list_price,
            'order_id': self.sale_order.id,
        })
        sale_order_line2.product_id_change()
        self.sale_order._compute_tax_id()
        self.sale_order.action_confirm()

        # create invoice lines and validate it
        move_form = Form(self.AccountMove)
        move_form.partner_id = self.partner_customer_usd
        with move_form.line_ids.new() as line_form:
            line_form.product_id = self.product_deliver_sales_price
            line_form.quantity = 3.0
            line_form.analytic_account_id = self.analytic_account
        with move_form.line_ids.new() as line_form:
            line_form.product_id = self.product_order_sales_price
            line_form.quantity = 3.0
            line_form.analytic_account_id = self.analytic_account
        invoice_a = move_form.save()
        invoice_a.post()

        sale_order_line3 = self.sale_order.order_line.filtered(lambda sol: sol != sale_order_line1 and sol.product_id == self.product_deliver_sales_price)
        sale_order_line4 = self.sale_order.order_line.filtered(lambda sol: sol != sale_order_line2 and sol.product_id == self.product_order_sales_price)

        self.assertTrue(sale_order_line3, "A new sale line should have been created with ordered product")
        self.assertTrue(sale_order_line4, "A new sale line should have been created with delivered product")
        self.assertEquals(len(self.sale_order.order_line), 4, "There should be 4 lines on the SO (2 vendor bill lines created)")
        self.assertEquals(len(self.sale_order.order_line.filtered(lambda sol: sol.is_expense)), 2, "There should be 4 lines on the SO (2 vendor bill lines created)")

        self.assertEquals(sale_order_line1.qty_delivered, 1, "Exising SO line 1 should not be impacted by reinvoicing product at cost")
        self.assertEquals(sale_order_line2.qty_delivered, 1, "Exising SO line 2 should not be impacted by reinvoicing product at cost")

        self.assertEquals((sale_order_line3.price_unit, sale_order_line3.qty_delivered, sale_order_line3.product_uom_qty, sale_order_line3.qty_invoiced), (self.product_deliver_sales_price.list_price, 3, 0, 0), 'Sale line is wrong after confirming vendor invoice')
        self.assertEquals((sale_order_line4.price_unit, sale_order_line4.qty_delivered, sale_order_line4.product_uom_qty, sale_order_line4.qty_invoiced), (self.product_order_sales_price.list_price, 3, 0, 0), 'Sale line is wrong after confirming vendor invoice')

        self.assertEquals(sale_order_line3.qty_delivered_method, 'analytic', "Delivered quantity of 'expense' SO line 3 should be computed by analytic amount")
        self.assertEquals(sale_order_line4.qty_delivered_method, 'analytic', "Delivered quantity of 'expense' SO line 4 should be computed by analytic amount")

        # create second invoice lines and validate it
        move_form = Form(self.AccountMove)
        move_form.partner_id = self.partner_customer_usd
        with move_form.line_ids.new() as line_form:
            line_form.product_id = self.product_deliver_sales_price
            line_form.quantity = 2.0
            line_form.analytic_account_id = self.analytic_account
        with move_form.line_ids.new() as line_form:
            line_form.product_id = self.product_order_sales_price
            line_form.quantity = 2.0
            line_form.analytic_account_id = self.analytic_account
        invoice_b = move_form.save()
        invoice_b.post()

        sale_order_line5 = self.sale_order.order_line.filtered(lambda sol: sol != sale_order_line1 and sol != sale_order_line3 and sol.product_id == self.product_deliver_sales_price)
        sale_order_line6 = self.sale_order.order_line.filtered(lambda sol: sol != sale_order_line2 and sol != sale_order_line4 and sol.product_id == self.product_order_sales_price)

        self.assertFalse(sale_order_line5, "No new sale line should have been created with delivered product !!")
        self.assertTrue(sale_order_line6, "A new sale line should have been created with ordered product")

        self.assertEquals(len(self.sale_order.order_line), 5, "There should be 5 lines on the SO, 1 new created and 1 incremented")
        self.assertEquals(len(self.sale_order.order_line.filtered(lambda sol: sol.is_expense)), 3, "There should be 3 expenses lines on the SO")

        self.assertEquals((sale_order_line6.price_unit, sale_order_line6.qty_delivered, sale_order_line4.product_uom_qty, sale_order_line6.qty_invoiced), (self.product_order_sales_price.list_price, 2, 0, 0), 'Sale line is wrong after confirming 2e vendor invoice')

    def test_no_expense(self):
        """ Test invoicing vendor bill with no policy. Check nothing happen. """
        # confirm SO
        sale_order_line = self.env['sale.order.line'].create({
            'name': self.product_no_expense.name,
            'product_id': self.product_no_expense.id,
            'product_uom_qty': 2,
            'qty_delivered': 1,
            'product_uom': self.product_no_expense.uom_id.id,
            'price_unit': self.product_no_expense.list_price,
            'order_id': self.sale_order.id,
        })
        self.sale_order._compute_tax_id()
        self.sale_order.action_confirm()

        # create invoice lines and validate it
        invoice_a = self.AccountMove.create({
            'partner_id': self.partner_customer_usd.id,
            'journal_id': self.journal_purchase.id,
            'line_ids': [
                (0, 0, {
                    'product_id': self.product_no_expense.id,
                    'quantity': 3,
                    'analytic_account_id': self.analytic_account.id,
                }),
            ],
        })
        invoice_a.post()

        self.assertEquals(len(self.sale_order.order_line), 1, "No SO line should have been created (or removed) when validating vendor bill")
        self.assertEquals(sale_order_line.qty_delivered, 1, "The delivered quantity of SO line should not have been incremented")
        self.assertTrue(invoice_a.mapped('line_ids.analytic_line_ids'), "Analytic lines should be generated")
