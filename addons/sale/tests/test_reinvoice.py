# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from freezegun import freeze_time
from odoo.addons.sale.tests.common import TestSaleCommon
from odoo.tests import Form, tagged


@tagged('post_install', '-at_install')
class TestReInvoice(TestSaleCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.analytic_plan = cls.env['account.analytic.plan'].create({
            'name': 'Plan',
        })

        cls.analytic_account = cls.env['account.analytic.account'].create({
            'name': 'Test AA',
            'code': 'TESTSALE_REINVOICE',
            'company_id': cls.partner_a.company_id.id,
            'plan_id': cls.analytic_plan.id,
            'partner_id': cls.partner_a.id
        })

        cls.sale_order = cls.env['sale.order'].with_context(mail_notrack=True, mail_create_nolog=True).create({
            'partner_id': cls.partner_a.id,
            'partner_invoice_id': cls.partner_a.id,
            'partner_shipping_id': cls.partner_a.id,
            'analytic_account_id': cls.analytic_account.id,
            'pricelist_id': cls.company_data['default_pricelist'].id,
        })

        cls.AccountMove = cls.env['account.move'].with_context(
            default_move_type='in_invoice',
            default_invoice_date=cls.sale_order.date_order,
            mail_notrack=True,
            mail_create_nolog=True,
        )

    def test_at_cost(self):
        # Required for `analytic_account_id` to be visible in the view
        self.env.user.groups_id += self.env.ref('analytic.group_analytic_accounting')
        """ Test vendor bill at cost for product based on ordered and delivered quantities. """
        # create SO line and confirm SO (with only one line)
        sale_order_line1 = self.env['sale.order.line'].create({
            'product_id': self.company_data['product_order_cost'].id,
            'product_uom_qty': 2,
            'qty_delivered': 1,
            'order_id': self.sale_order.id,
        })
        sale_order_line2 = self.env['sale.order.line'].create({
            'product_id': self.company_data['product_delivery_cost'].id,
            'product_uom_qty': 4,
            'qty_delivered': 1,
            'order_id': self.sale_order.id,
        })

        self.sale_order.action_confirm()

        # create invoice lines and validate it
        move_form = Form(self.AccountMove)
        move_form.partner_id = self.partner_a
        with move_form.invoice_line_ids.new() as line_form:
            line_form.product_id = self.company_data['product_order_cost']
            line_form.quantity = 3.0
            line_form.analytic_distribution = {self.analytic_account.id: 100}
        with move_form.invoice_line_ids.new() as line_form:
            line_form.product_id = self.company_data['product_delivery_cost']
            line_form.quantity = 3.0
            line_form.analytic_distribution = {self.analytic_account.id: 100}
        invoice_a = move_form.save()
        invoice_a.action_post()

        sale_order_line3 = self.sale_order.order_line.filtered(lambda sol: sol != sale_order_line1 and sol.product_id == self.company_data['product_order_cost'])
        sale_order_line4 = self.sale_order.order_line.filtered(lambda sol: sol != sale_order_line2 and sol.product_id == self.company_data['product_delivery_cost'])

        self.assertTrue(sale_order_line3, "A new sale line should have been created with ordered product")
        self.assertTrue(sale_order_line4, "A new sale line should have been created with delivered product")
        self.assertEqual(len(self.sale_order.order_line), 4, "There should be 4 lines on the SO (2 vendor bill lines created)")
        self.assertEqual(len(self.sale_order.order_line.filtered(lambda sol: sol.is_expense)), 2, "There should be 4 lines on the SO (2 vendor bill lines created)")

        self.assertEqual((sale_order_line3.price_unit, sale_order_line3.qty_delivered, sale_order_line3.product_uom_qty, sale_order_line3.qty_invoiced), (self.company_data['product_order_cost'].standard_price, 3, 0, 0), 'Sale line is wrong after confirming vendor invoice')
        self.assertEqual((sale_order_line4.price_unit, sale_order_line4.qty_delivered, sale_order_line4.product_uom_qty, sale_order_line4.qty_invoiced), (self.company_data['product_delivery_cost'].standard_price, 3, 0, 0), 'Sale line is wrong after confirming vendor invoice')

        self.assertEqual(sale_order_line3.qty_delivered_method, 'analytic', "Delivered quantity of 'expense' SO line should be computed by analytic amount")
        self.assertEqual(sale_order_line4.qty_delivered_method, 'analytic', "Delivered quantity of 'expense' SO line should be computed by analytic amount")

        # create second invoice lines and validate it
        move_form = Form(self.AccountMove)
        move_form.partner_id = self.partner_a
        with move_form.invoice_line_ids.new() as line_form:
            line_form.product_id = self.company_data['product_order_cost']
            line_form.quantity = 2.0
            line_form.analytic_distribution = {self.analytic_account.id: 100}
        with move_form.invoice_line_ids.new() as line_form:
            line_form.product_id = self.company_data['product_delivery_cost']
            line_form.quantity = 2.0
            line_form.analytic_distribution = {self.analytic_account.id: 100}
        invoice_b = move_form.save()
        invoice_b.action_post()

        sale_order_line5 = self.sale_order.order_line.filtered(lambda sol: sol != sale_order_line1 and sol != sale_order_line3 and sol.product_id == self.company_data['product_order_cost'])
        sale_order_line6 = self.sale_order.order_line.filtered(lambda sol: sol != sale_order_line2 and sol != sale_order_line4 and sol.product_id == self.company_data['product_delivery_cost'])

        self.assertTrue(sale_order_line5, "A new sale line should have been created with ordered product")
        self.assertTrue(sale_order_line6, "A new sale line should have been created with delivered product")

        self.assertEqual(len(self.sale_order.order_line), 6, "There should be still 4 lines on the SO, no new created")
        self.assertEqual(len(self.sale_order.order_line.filtered(lambda sol: sol.is_expense)), 4, "There should be still 2 expenses lines on the SO")

        self.assertEqual((sale_order_line5.price_unit, sale_order_line5.qty_delivered, sale_order_line5.product_uom_qty, sale_order_line5.qty_invoiced), (self.company_data['product_order_cost'].standard_price, 2, 0, 0), 'Sale line 5 is wrong after confirming 2e vendor invoice')
        self.assertEqual((sale_order_line6.price_unit, sale_order_line6.qty_delivered, sale_order_line6.product_uom_qty, sale_order_line6.qty_invoiced), (self.company_data['product_delivery_cost'].standard_price, 2, 0, 0), 'Sale line 6 is wrong after confirming 2e vendor invoice')

    @freeze_time('2020-01-15')
    def test_sales_team_invoiced(self):
        """ Test invoiced field from  sales team ony take into account the amount the sales channel has invoiced this month """

        invoices = self.env['account.move'].create([
            {
                'move_type': 'out_invoice',
                'partner_id': self.partner_a.id,
                'invoice_date': '2020-01-10',
                'invoice_line_ids': [(0, 0, {'product_id': self.product_a.id, 'price_unit': 1000.0})],
            },
            {
                'move_type': 'out_refund',
                'partner_id': self.partner_a.id,
                'invoice_date': '2020-01-10',
                'invoice_line_ids': [(0, 0, {'product_id': self.product_a.id, 'price_unit': 500.0})],
            },
            {
                'move_type': 'in_invoice',
                'partner_id': self.partner_a.id,
                'invoice_date': '2020-01-01',
                'date': '2020-01-01',
                'invoice_line_ids': [(0, 0, {'product_id': self.product_a.id, 'price_unit': 800.0})],
            },
        ])
        invoices.action_post()

        for invoice in invoices:
            self.env['account.payment.register']\
                .with_context(active_model='account.move', active_ids=invoice.ids)\
                .create({})\
                ._create_payments()

        invoices.flush_model()
        self.assertRecordValues(invoices.team_id, [{'invoiced': 500.0}])

    def test_sales_price(self):
        """ Test invoicing vendor bill at sales price for products based on delivered and ordered quantities. Check no existing SO line is incremented, but when invoicing a
            second time, increment only the delivered so line.
        """
        # Required for `analytic_account_id` to be visible in the view
        self.env.user.groups_id += self.env.ref('analytic.group_analytic_accounting')
        # create SO line and confirm SO (with only one line)
        sale_order_line1 = self.env['sale.order.line'].create({
            'product_id': self.company_data['product_delivery_sales_price'].id,
            'product_uom_qty': 2,
            'qty_delivered': 1,
            'order_id': self.sale_order.id,
        })
        sale_order_line2 = self.env['sale.order.line'].create({
            'product_id': self.company_data['product_order_sales_price'].id,
            'product_uom_qty': 3,
            'qty_delivered': 1,
            'order_id': self.sale_order.id,
        })
        self.sale_order.action_confirm()

        # create invoice lines and validate it
        move_form = Form(self.AccountMove)
        move_form.partner_id = self.partner_a
        with move_form.invoice_line_ids.new() as line_form:
            line_form.product_id = self.company_data['product_delivery_sales_price']
            line_form.quantity = 3.0
            line_form.analytic_distribution = {self.analytic_account.id: 100}
        with move_form.invoice_line_ids.new() as line_form:
            line_form.product_id = self.company_data['product_order_sales_price']
            line_form.quantity = 3.0
            line_form.analytic_distribution = {self.analytic_account.id: 100}
        invoice_a = move_form.save()
        invoice_a.action_post()

        sale_order_line3 = self.sale_order.order_line.filtered(lambda sol: sol != sale_order_line1 and sol.product_id == self.company_data['product_delivery_sales_price'])
        sale_order_line4 = self.sale_order.order_line.filtered(lambda sol: sol != sale_order_line2 and sol.product_id == self.company_data['product_order_sales_price'])

        self.assertTrue(sale_order_line3, "A new sale line should have been created with ordered product")
        self.assertTrue(sale_order_line4, "A new sale line should have been created with delivered product")
        self.assertEqual(len(self.sale_order.order_line), 4, "There should be 4 lines on the SO (2 vendor bill lines created)")
        self.assertEqual(len(self.sale_order.order_line.filtered(lambda sol: sol.is_expense)), 2, "There should be 4 lines on the SO (2 vendor bill lines created)")

        self.assertEqual((sale_order_line3.price_unit, sale_order_line3.qty_delivered, sale_order_line3.product_uom_qty, sale_order_line3.qty_invoiced), (self.company_data['product_delivery_sales_price'].list_price, 3, 0, 0), 'Sale line is wrong after confirming vendor invoice')
        self.assertEqual((sale_order_line4.price_unit, sale_order_line4.qty_delivered, sale_order_line4.product_uom_qty, sale_order_line4.qty_invoiced), (self.company_data['product_order_sales_price'].list_price, 3, 0, 0), 'Sale line is wrong after confirming vendor invoice')

        self.assertEqual(sale_order_line3.qty_delivered_method, 'analytic', "Delivered quantity of 'expense' SO line 3 should be computed by analytic amount")
        self.assertEqual(sale_order_line4.qty_delivered_method, 'analytic', "Delivered quantity of 'expense' SO line 4 should be computed by analytic amount")

        # create second invoice lines and validate it
        move_form = Form(self.AccountMove)
        move_form.partner_id = self.partner_a
        with move_form.invoice_line_ids.new() as line_form:
            line_form.product_id = self.company_data['product_delivery_sales_price']
            line_form.quantity = 2.0
            line_form.analytic_distribution = {self.analytic_account.id: 100}
        with move_form.invoice_line_ids.new() as line_form:
            line_form.product_id = self.company_data['product_order_sales_price']
            line_form.quantity = 2.0
            line_form.analytic_distribution = {self.analytic_account.id: 100}
        invoice_b = move_form.save()
        invoice_b.action_post()

        sale_order_line5 = self.sale_order.order_line.filtered(lambda sol: sol != sale_order_line1 and sol != sale_order_line3 and sol.product_id == self.company_data['product_delivery_sales_price'])
        sale_order_line6 = self.sale_order.order_line.filtered(lambda sol: sol != sale_order_line2 and sol != sale_order_line4 and sol.product_id == self.company_data['product_order_sales_price'])

        self.assertFalse(sale_order_line5, "No new sale line should have been created with delivered product !!")
        self.assertTrue(sale_order_line6, "A new sale line should have been created with ordered product")

        self.assertEqual(len(self.sale_order.order_line), 5, "There should be 5 lines on the SO, 1 new created and 1 incremented")
        self.assertEqual(len(self.sale_order.order_line.filtered(lambda sol: sol.is_expense)), 3, "There should be 3 expenses lines on the SO")

        self.assertEqual((sale_order_line6.price_unit, sale_order_line6.qty_delivered, sale_order_line4.product_uom_qty, sale_order_line6.qty_invoiced), (self.company_data['product_order_sales_price'].list_price, 2, 0, 0), 'Sale line is wrong after confirming 2e vendor invoice')

    def test_no_expense(self):
        """ Test invoicing vendor bill with no policy. Check nothing happen. """
        # Required for `analytic_account_id` to be visible in the view
        self.env.user.groups_id += self.env.ref('analytic.group_analytic_accounting')
        # confirm SO
        sale_order_line = self.env['sale.order.line'].create({
            'product_id': self.company_data['product_delivery_no'].id,
            'product_uom_qty': 2,
            'qty_delivered': 1,
            'order_id': self.sale_order.id,
        })
        self.sale_order.action_confirm()

        # create invoice lines and validate it
        move_form = Form(self.AccountMove)
        move_form.partner_id = self.partner_a
        with move_form.invoice_line_ids.new() as line_form:
            line_form.product_id = self.company_data['product_delivery_no']
            line_form.quantity = 3.0
            line_form.analytic_distribution = {self.analytic_account.id: 100}
        invoice_a = move_form.save()
        invoice_a.action_post()

        self.assertEqual(len(self.sale_order.order_line), 1, "No SO line should have been created (or removed) when validating vendor bill")
        self.assertTrue(invoice_a.mapped('line_ids.analytic_line_ids'), "Analytic lines should be generated")

    def test_not_reinvoicing_invoiced_so_lines(self):
        """ Test that invoiced SO lines are not re-invoiced. """
        so_line1 = self.env['sale.order.line'].create({
            'product_id': self.company_data['product_delivery_cost'].id,
            'discount': 100.00,
            'order_id': self.sale_order.id,
        })
        so_line2 = self.env['sale.order.line'].create({
            'product_id': self.company_data['product_delivery_sales_price'].id,
            'discount': 100.00,
            'order_id': self.sale_order.id,
        })

        self.sale_order.action_confirm()

        for line in self.sale_order.order_line:
            line.qty_delivered = 1
        # create invoice and validate it
        invoice = self.sale_order._create_invoices()
        invoice.action_post()

        so_line3 = self.sale_order.order_line.filtered(lambda sol: sol != so_line1 and sol.product_id == self.company_data['product_delivery_cost'])
        so_line4 = self.sale_order.order_line.filtered(lambda sol: sol != so_line2 and sol.product_id == self.company_data['product_delivery_sales_price'])

        self.assertFalse(so_line3, "No re-invoicing should have created a new sale line with product #1")
        self.assertFalse(so_line4, "No re-invoicing should have created a new sale line with product #2")
        self.assertEqual(so_line1.qty_delivered, 1, "No re-invoicing should have impacted exising SO line 1")
        self.assertEqual(so_line2.qty_delivered, 1, "No re-invoicing should have impacted exising SO line 2")

    def test_not_recomputing_unit_price_for_expensed_so_lines(self):
        # Required for `analytic_account_id` to be visible in the view
        self.env.user.groups_id += self.env.ref('analytic.group_analytic_accounting')

        # create SO line and confirm SO (with only one line)
        sol_1 = self.env['sale.order.line'].create({
            'product_id': self.company_data['product_order_cost'].id,
            'product_uom_qty': 2,
            'qty_delivered': 1,
            'order_id': self.sale_order.id,
        })
        self.sale_order.action_confirm()

        # create invoice lines and validate it
        move_form = Form(self.AccountMove)
        move_form.partner_id = self.partner_a
        with move_form.invoice_line_ids.new() as line_form:
            line_form.product_id = self.company_data['product_order_cost']
            line_form.quantity = 3.0
            line_form.analytic_distribution = {self.analytic_account.id: 100}
        invoice = move_form.save()
        invoice.action_post()

        # update the quantity of the expensed line
        sol_2 = self.sale_order.order_line.filtered(lambda sol: sol != sol_1 and sol.product_id == self.company_data['product_order_cost'])

        sol_2_subtotal_before = sol_2.price_unit
        sol_2.product_uom_qty = 3.0
        sol_2_subtotal_after = sol_2.price_unit

        self.assertEqual(sol_2_subtotal_before, sol_2_subtotal_after)
