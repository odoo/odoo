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

        cls.analytic_account = cls.env['account.analytic.account'].create({
            'name': 'Test AA',
            'code': 'TESTSALE_REINVOICE',
            'company_id': cls.partner_a.company_id.id,
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

    def _create_sol(self, sale_order, product):
        return self.env['sale.order.line'].create({
            'name': product.name,
            'product_id': product.id,
            'product_uom_qty': 1,
            'qty_delivered': 0,
            'product_uom': product.uom_id.id,
            'price_unit': product.list_price,
            'order_id': sale_order.id,
        })

    def test_at_cost(self):
        """ Test vendor bill at cost for product based on ordered and delivered quantities. """
        # create SO line and confirm SO (with only one line)
        sale_order_line1 = self.env['sale.order.line'].create({
            'name': self.company_data['product_order_cost'].name,
            'product_id': self.company_data['product_order_cost'].id,
            'product_uom_qty': 2,
            'qty_delivered': 1,
            'product_uom': self.company_data['product_order_cost'].uom_id.id,
            'price_unit': self.company_data['product_order_cost'].list_price,
            'order_id': self.sale_order.id,
        })
        sale_order_line1.product_id_change()
        sale_order_line2 = self.env['sale.order.line'].create({
            'name': self.company_data['product_delivery_cost'].name,
            'product_id': self.company_data['product_delivery_cost'].id,
            'product_uom_qty': 4,
            'qty_delivered': 1,
            'product_uom': self.company_data['product_delivery_cost'].uom_id.id,
            'price_unit': self.company_data['product_delivery_cost'].list_price,
            'order_id': self.sale_order.id,
        })
        sale_order_line2.product_id_change()

        self.sale_order.onchange_partner_id()
        self.sale_order._compute_tax_id()
        self.sale_order.action_confirm()

        # create invoice lines and validate it
        move_form = Form(self.AccountMove)
        move_form.partner_id = self.partner_a
        with move_form.line_ids.new() as line_form:
            line_form.product_id = self.company_data['product_order_cost']
            line_form.quantity = 3.0
            line_form.analytic_account_id = self.analytic_account
        with move_form.line_ids.new() as line_form:
            line_form.product_id = self.company_data['product_delivery_cost']
            line_form.quantity = 3.0
            line_form.analytic_account_id = self.analytic_account
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
        with move_form.line_ids.new() as line_form:
            line_form.product_id = self.company_data['product_order_cost']
            line_form.quantity = 2.0
            line_form.analytic_account_id = self.analytic_account
        with move_form.line_ids.new() as line_form:
            line_form.product_id = self.company_data['product_delivery_cost']
            line_form.quantity = 2.0
            line_form.analytic_account_id = self.analytic_account
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

        invoices.flush()
        self.assertRecordValues(invoices.team_id, [{'invoiced': 500.0}])

    def test_sales_price(self):
        """ Test invoicing vendor bill at sales price for products based on delivered and ordered quantities. Check no existing SO line is incremented, but when invoicing a
            second time, increment only the delivered so line.
        """
        # create SO line and confirm SO (with only one line)
        sale_order_line1 = self.env['sale.order.line'].create({
            'name': self.company_data['product_delivery_sales_price'].name,
            'product_id': self.company_data['product_delivery_sales_price'].id,
            'product_uom_qty': 2,
            'qty_delivered': 1,
            'product_uom': self.company_data['product_delivery_sales_price'].uom_id.id,
            'price_unit': self.company_data['product_delivery_sales_price'].list_price,
            'order_id': self.sale_order.id,
        })
        sale_order_line1.product_id_change()
        sale_order_line2 = self.env['sale.order.line'].create({
            'name': self.company_data['product_order_sales_price'].name,
            'product_id': self.company_data['product_order_sales_price'].id,
            'product_uom_qty': 3,
            'qty_delivered': 1,
            'product_uom': self.company_data['product_order_sales_price'].uom_id.id,
            'price_unit': self.company_data['product_order_sales_price'].list_price,
            'order_id': self.sale_order.id,
        })
        sale_order_line2.product_id_change()
        self.sale_order._compute_tax_id()
        self.sale_order.action_confirm()

        # create invoice lines and validate it
        move_form = Form(self.AccountMove)
        move_form.partner_id = self.partner_a
        with move_form.line_ids.new() as line_form:
            line_form.product_id = self.company_data['product_delivery_sales_price']
            line_form.quantity = 3.0
            line_form.analytic_account_id = self.analytic_account
        with move_form.line_ids.new() as line_form:
            line_form.product_id = self.company_data['product_order_sales_price']
            line_form.quantity = 3.0
            line_form.analytic_account_id = self.analytic_account
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
        with move_form.line_ids.new() as line_form:
            line_form.product_id = self.company_data['product_delivery_sales_price']
            line_form.quantity = 2.0
            line_form.analytic_account_id = self.analytic_account
        with move_form.line_ids.new() as line_form:
            line_form.product_id = self.company_data['product_order_sales_price']
            line_form.quantity = 2.0
            line_form.analytic_account_id = self.analytic_account
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
        # confirm SO
        sale_order_line = self.env['sale.order.line'].create({
            'name': self.company_data['product_delivery_no'].name,
            'product_id': self.company_data['product_delivery_no'].id,
            'product_uom_qty': 2,
            'qty_delivered': 1,
            'product_uom': self.company_data['product_delivery_no'].uom_id.id,
            'price_unit': self.company_data['product_delivery_no'].list_price,
            'order_id': self.sale_order.id,
        })
        self.sale_order._compute_tax_id()
        self.sale_order.action_confirm()

        # create invoice lines and validate it
        move_form = Form(self.AccountMove)
        move_form.partner_id = self.partner_a
        with move_form.line_ids.new() as line_form:
            line_form.product_id = self.company_data['product_delivery_no']
            line_form.quantity = 3.0
            line_form.analytic_account_id = self.analytic_account
        invoice_a = move_form.save()
        invoice_a.action_post()

        self.assertEqual(len(self.sale_order.order_line), 1, "No SO line should have been created (or removed) when validating vendor bill")
        self.assertTrue(invoice_a.mapped('line_ids.analytic_line_ids'), "Analytic lines should be generated")

    def test_not_reinvoicing_invoiced_so_lines(self):
        """ Test that invoiced SO lines are not re-invoiced. """
        so_line1 = self.env['sale.order.line'].create({
            'name': self.company_data['product_delivery_cost'].name,
            'product_id': self.company_data['product_delivery_cost'].id,
            'product_uom_qty': 1,
            'product_uom': self.company_data['product_delivery_cost'].uom_id.id,
            'price_unit': self.company_data['product_delivery_cost'].list_price,
            'discount': 100.00,
            'order_id': self.sale_order.id,
        })
        so_line1.product_id_change()
        so_line2 = self.env['sale.order.line'].create({
            'name': self.company_data['product_delivery_sales_price'].name,
            'product_id': self.company_data['product_delivery_sales_price'].id,
            'product_uom_qty': 1,
            'product_uom': self.company_data['product_delivery_sales_price'].uom_id.id,
            'price_unit': self.company_data['product_delivery_sales_price'].list_price,
            'discount': 100.00,
            'order_id': self.sale_order.id,
        })
        so_line2.product_id_change()

        self.sale_order.onchange_partner_id()
        self.sale_order._compute_tax_id()
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

    def test_refund_delivered_reinvoiced(self):
        """
        Tests that when we refund a re-invoiced expense, the Quantity Delivered on the Sale Order Line is updated
        - (1) We create a Sale Order
        - (2) We create a bill to be re-invoiced
        - (3) We create a partial credit note
        -> The sale order lines created in (2) should be updated during (3) with the correct delivered quantity.
        """
        # create the setup
        product_1 = self.company_data['product_order_cost']
        product_2 = self.env['product.product'].create({
            'name': 'Great Product',
            'standard_price': 50.0,
            'list_price': 100.0,
            'type': 'consu',
            'uom_id': self.env.ref('uom.product_uom_unit').id,
            'uom_po_id': self.env.ref('uom.product_uom_unit').id,
            'invoice_policy': 'order',
            'expense_policy': 'cost',
        })
        self._create_sol(self.sale_order, product_1)
        self._create_sol(self.sale_order, product_2)
        self.sale_order.action_confirm()

        # create the bill to be re-invoiced
        bill_form = Form(self.AccountMove.with_context(default_move_type='in_invoice'))
        bill_form.partner_id = self.partner_b
        with bill_form.line_ids.new() as line_form:
            line_form.product_id = product_1
            line_form.quantity = 20.0
            line_form.analytic_account_id = self.analytic_account
        with bill_form.line_ids.new() as line_form:
            line_form.product_id = product_2
            line_form.quantity = 20.0
            line_form.analytic_account_id = self.analytic_account
        bill = bill_form.save()
        bill.action_post()

        self.assertRecordValues(self.sale_order.order_line[-2:], [{'qty_delivered': 20}, {'qty_delivered': 20}])

        # create partial credit note
        rbill_form = Form(bill._reverse_moves([{'invoice_date': '2023-03-31'}]))
        with rbill_form.invoice_line_ids.edit(0) as line_form:
            line_form.quantity = 10
        with rbill_form.invoice_line_ids.edit(1) as line_form:
            line_form.quantity = 5
        rbill = rbill_form.save()
        rbill.action_post()

        self.assertRecordValues(self.sale_order.order_line[-2:], [{'qty_delivered': 10}, {'qty_delivered': 15}])
