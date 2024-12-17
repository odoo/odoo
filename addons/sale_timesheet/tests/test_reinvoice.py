# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import timedelta

from odoo.addons.sale_timesheet.tests.common import TestCommonSaleTimesheet

from odoo.fields import Date
from odoo.tests import Form, tagged


@tagged('-at_install', 'post_install')
class TestReInvoice(TestCommonSaleTimesheet):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # patch expense products to make them services creating task/project
        service_values = {
            'type': 'service',
            'service_type': 'timesheet',
            'service_tracking': 'task_in_project'
        }
        cls.company_data['product_order_no'].write(service_values)
        service_values['expense_policy'] = 'cost'
        cls.company_data['product_order_cost'].write(service_values)
        cls.company_data['product_delivery_cost'].write(service_values)
        service_values['expense_policy'] = 'sales_price'
        cls.company_data['product_order_sales_price'].write(service_values)
        cls.company_data['product_delivery_sales_price'].write(service_values)

        # create AA, SO and invoices
        cls.analytic_plan = cls.env['account.analytic.plan'].create({
            'name': 'Timesheet Plan',
        })

        cls.analytic_account = cls.env['account.analytic.account'].create({
            'name': 'Test AA',
            'code': 'TESTSALE_TIMESHEET_REINVOICE',
            'company_id': cls.company_data['company'].id,
            'plan_id': cls.analytic_plan.id,
            'partner_id': cls.partner_a.id
        })

        cls.project = cls.env['project.project'].create({
            'name': 'SO Project',
            'allow_timesheets': False,
            f'{cls.analytic_plan._column_name()}': cls.analytic_account.id,
        })

        cls.sale_order = cls.env['sale.order'].create({
            'partner_id': cls.partner_a.id,
            'partner_invoice_id': cls.partner_a.id,
            'partner_shipping_id': cls.partner_a.id,
            'project_id': cls.project.id,
        })

        cls.Invoice = cls.env['account.move'].with_context(
            default_move_type='in_invoice',
            default_invoice_date=cls.sale_order.date_order,
        )

    def test_at_cost(self):
        """ Test vendor bill at cost for product based on ordered and delivered quantities. """
        # Required for `analytic_distribution` to be visible in the view
        self.env.user.groups_id += self.env.ref('analytic.group_analytic_accounting')
        # create SO line and confirm SO (with only one line)
        sale_order_line1 = self.env['sale.order.line'].create({
            'product_id': self.company_data['product_order_cost'].id,
            'product_uom_qty': 2,
            'order_id': self.sale_order.id,
        })
        sale_order_line2 = self.env['sale.order.line'].create({
            'product_id': self.company_data['product_delivery_cost'].id,
            'product_uom_qty': 4,
            'order_id': self.sale_order.id,
        })

        self.sale_order.action_confirm()

        self.assertEqual(sale_order_line1.qty_delivered_method, 'timesheet', "Delivered quantity of 'service' SO line should be computed by timesheet amount")
        self.assertEqual(sale_order_line2.qty_delivered_method, 'timesheet', "Delivered quantity of 'service' SO line should be computed by timesheet amount")

        # let's log some timesheets (on the project created by sale_order_line1)
        task_sol1 = sale_order_line1.task_id
        self.env['account.analytic.line'].create({
            'name': 'Test Line',
            'project_id': task_sol1.project_id.id,
            'task_id': task_sol1.id,
            'unit_amount': 1,
            'employee_id': self.employee_user.id,
            'company_id': self.company_data['company'].id,
        })

        move_form = Form(self.Invoice)
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

        self.assertEqual(sale_order_line1.qty_delivered, 1, "Exising SO line 1 should not be impacted by reinvoicing product at cost")
        self.assertEqual(sale_order_line2.qty_delivered, 0, "Exising SO line 2 should not be impacted by reinvoicing product at cost")

        self.assertFalse(sale_order_line3.task_id, "Adding a new expense SO line should not create a task (sol3)")
        self.assertFalse(sale_order_line4.task_id, "Adding a new expense SO line should not create a task (sol4)")
        self.assertEqual(len(self.sale_order.project_ids), 1, "SO create only one project with its service line. Adding new expense SO line should not impact that")

        self.assertEqual((sale_order_line3.price_unit, sale_order_line3.qty_delivered, sale_order_line3.product_uom_qty, sale_order_line3.qty_invoiced), (self.company_data['product_order_cost'].standard_price, 3.0, 3.0, 0), 'Sale line is wrong after confirming vendor invoice')
        self.assertEqual((sale_order_line4.price_unit, sale_order_line4.qty_delivered, sale_order_line4.product_uom_qty, sale_order_line4.qty_invoiced), (self.company_data['product_delivery_cost'].standard_price, 3.0, 3.0, 0), 'Sale line is wrong after confirming vendor invoice')

        self.assertEqual(sale_order_line3.qty_delivered_method, 'analytic', "Delivered quantity of 'expense' SO line should be computed by analytic amount")
        self.assertEqual(sale_order_line4.qty_delivered_method, 'analytic', "Delivered quantity of 'expense' SO line should be computed by analytic amount")

        # create second invoice lines and validate it
        move_form = Form(self.Invoice)
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

        self.assertEqual((sale_order_line5.price_unit, sale_order_line5.qty_delivered, sale_order_line5.product_uom_qty, sale_order_line5.qty_invoiced), (self.company_data['product_order_cost'].standard_price, 2.0, 2.0, 0), 'Sale line 5 is wrong after confirming 2e vendor invoice')
        self.assertEqual((sale_order_line6.price_unit, sale_order_line6.qty_delivered, sale_order_line6.product_uom_qty, sale_order_line6.qty_invoiced), (self.company_data['product_delivery_cost'].standard_price, 2.0, 2.0, 0), 'Sale line 6 is wrong after confirming 2e vendor invoice')

    def test_sales_price(self):
        """ Test invoicing vendor bill at sales price for products based on delivered and ordered quantities. Check no existing SO line is incremented, but when invoicing a
            second time, increment only the delivered so line.
        """
        # Required for `analytic_distribution` to be visible in the view
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

        # let's log some timesheets (on the project created by sale_order_line1)
        task_sol1 = sale_order_line1.task_id
        self.env['account.analytic.line'].create({
            'name': 'Test Line',
            'project_id': task_sol1.project_id.id,
            'task_id': task_sol1.id,
            'unit_amount': 1,
            'employee_id': self.employee_user.id,
        })

        # create invoice lines and validate it
        move_form = Form(self.Invoice)
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

        self.assertEqual(sale_order_line1.qty_delivered, 1, "Exising SO line 1 should not be impacted by reinvoicing product at cost")
        self.assertEqual(sale_order_line2.qty_delivered, 0, "Exising SO line 2 should not be impacted by reinvoicing product at cost")

        self.assertFalse(sale_order_line3.task_id, "Adding a new expense SO line should not create a task (sol3)")
        self.assertFalse(sale_order_line4.task_id, "Adding a new expense SO line should not create a task (sol4)")
        self.assertEqual(len(self.sale_order.project_ids), 1, "SO create only one project with its service line. Adding new expense SO line should not impact that")

        self.assertEqual((sale_order_line3.price_unit, sale_order_line3.qty_delivered, sale_order_line3.product_uom_qty, sale_order_line3.qty_invoiced), (self.company_data['product_delivery_sales_price'].list_price, 3.0, 3.0, 0), 'Sale line is wrong after confirming vendor invoice')
        self.assertEqual((sale_order_line4.price_unit, sale_order_line4.qty_delivered, sale_order_line4.product_uom_qty, sale_order_line4.qty_invoiced), (self.company_data['product_order_sales_price'].list_price, 3.0, 3.0, 0), 'Sale line is wrong after confirming vendor invoice')

        self.assertEqual(sale_order_line3.qty_delivered_method, 'analytic', "Delivered quantity of 'expense' SO line 3 should be computed by analytic amount")
        self.assertEqual(sale_order_line4.qty_delivered_method, 'analytic', "Delivered quantity of 'expense' SO line 4 should be computed by analytic amount")

        # create second invoice lines and validate it
        move_form = Form(self.Invoice)
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

        self.assertEqual((sale_order_line6.price_unit, sale_order_line6.qty_delivered, sale_order_line4.product_uom_qty, sale_order_line6.qty_invoiced), (self.company_data['product_order_sales_price'].list_price, 2.0, 3.0, 0), 'Sale line is wrong after confirming 2e vendor invoice')

    def test_no_expense(self):
        """ Test invoicing vendor bill with no policy. Check nothing happen. """
        # Required for `analytic_distribution` to be visible in the view
        self.env.user.groups_id += self.env.ref('analytic.group_analytic_accounting')
        # confirm SO
        sale_order_line = self.env['sale.order.line'].create({
            'product_id': self.company_data['product_order_no'].id,
            'product_uom_qty': 2,
            'qty_delivered': 1,
            'order_id': self.sale_order.id,
        })
        self.sale_order.action_confirm()

        # create invoice lines and validate it
        move_form = Form(self.Invoice)
        move_form.partner_id = self.partner_a
        with move_form.invoice_line_ids.new() as line_form:
            line_form.product_id = self.company_data['product_order_no']
            line_form.quantity = 3.0
            line_form.analytic_distribution = {self.analytic_account.id: 100}
        invoice_a = move_form.save()
        invoice_a.action_post()

        # let's log some timesheets (on the project created by sale_order_line1)
        task_sol1 = sale_order_line.task_id
        self.env['account.analytic.line'].create({
            'name': 'Test Line',
            'project_id': task_sol1.project_id.id,
            'task_id': task_sol1.id,
            'unit_amount': 1,
            'employee_id': self.employee_user.id,
        })

        self.assertEqual(len(self.sale_order.order_line), 1, "No SO line should have been created (or removed) when validating vendor bill")
        self.assertEqual(sale_order_line.qty_delivered, 1, "The delivered quantity of SO line should not have been incremented")
        self.assertTrue(invoice_a.mapped('line_ids.analytic_line_ids'), "Analytic lines should be generated")

    def test_reversed_invoice_reinvoice_with_period(self):
        """
        Tests that when reversing an invoice of timesheet and selecting a time
        period, the qty to invoice is correctly found
        Business flow:
          Create a sale order and deliver some hours (invoiced = 0)
          Create an invoice
          Confirm (invoiced = 1)
          Add Credit Note
          Confirm (invoiced = 0)
          Go back to the SO
          Create an invoice
          Select a time period [1 week ago, 1 week in the future]
          Confirm
          -> Fails if there is nothing to invoice
        """
        product = self.env['product.product'].create({
            'name': "Service delivered, create task in global project",
            'standard_price': 30,
            'list_price': 90,
            'type': 'service',
            'service_policy': 'delivered_timesheet',
            'invoice_policy': 'delivery',
            'default_code': 'SERV-DELI2',
            'service_type': 'timesheet',
            'service_tracking': 'task_global_project',
            'project_id': self.project_global.id,
            'taxes_id': False,
            'property_account_income_id': self.account_sale.id,
        })
        today = Date.context_today(self.env.user)

        # Creates a sales order for quantity 3
        so_form = Form(self.env['sale.order'])
        so_form.partner_id = self.env['res.partner'].create({'name': 'Toto'})
        with so_form.order_line.new() as line:
            line.product_id = product
            line.product_uom_qty = 3.0
        sale_order = so_form.save()
        sale_order.action_confirm()

        # "Deliver" 1 of 3
        task = sale_order.tasks_ids
        self.env['account.analytic.line'].create({
            'name': 'Test Line',
            'project_id': task.project_id.id,
            'task_id': task.id,
            'unit_amount': 1,
            'employee_id': self.employee_user.id,
            'company_id': self.company_data['company'].id,
        })

        context = {
            "active_model": 'sale.order',
            "active_ids": [sale_order.id],
            "active_id": sale_order.id,
        }
        # Invoice the 1
        wizard = self.env['sale.advance.payment.inv'].with_context(context).create({
            'advance_payment_method': 'delivered'
        })
        invoice_dict = wizard.create_invoices()
        # Confirm the invoice
        invoice = self.env['account.move'].browse(invoice_dict['res_id'])
        invoice.action_post()

        # Refund the invoice
        wiz_context = {
            'active_model': 'account.move',
            'active_ids': [invoice.id],
            'default_journal_id': self.company_data['default_journal_sale'].id
        }
        refund_invoice_wiz = self.env['account.move.reversal'].with_context(wiz_context).create({
            'reason': 'please reverse :c',
            'date': today,
        })
        refund_invoice = self.env['account.move'].browse(refund_invoice_wiz.refund_moves()['res_id'])
        refund_invoice.action_post()
        # reversing with action_reverse and then action_post does not reset the invoice_status to 'to invoice' in tests

        # Recreate wizard to get the new invoices created
        wizard = self.env['sale.advance.payment.inv'].with_context(context).create({
            'advance_payment_method': 'delivered',
            'date_start_invoice_timesheet': today - timedelta(days=7),
            'date_end_invoice_timesheet': today + timedelta(days=7)
        })

        # The actual test :
        wizard.create_invoices()  # No exception should be raised, there is indeed something to be invoiced since it was reversed

    def test_project_update_reinvoiced_vendor_bill_product(self):
        project_product, expense_product = self.env['product.product'].create([{
            'name': 'Project creation',
            'type': 'service',
            'service_tracking': 'task_in_project',
        }, {
            'name': 'Expense Product',
            'expense_policy': 'sales_price',
            'list_price': 20,
        }])
        sale_order = self.env['sale.order'].create({'partner_id': self.partner_a.id})
        self.env['sale.order.line'].create({
            'product_id': project_product.id,
            'order_id': sale_order.id,
        })
        sale_order.action_confirm()
        project = sale_order.project_ids
        self.assertTrue(project, 'Project should have been created on sale order confirmation')

        vendor_bill = self.env['account.move'].create({
            'partner_id': self.partner_a.id,
            'invoice_date': sale_order.date_order,
            'journal_id': self.env['account.journal'].search([('code', '=', 'BILL'), ('company_id', '=', self.env.company.id)]).id,
            'move_type': 'in_invoice',
        })
        self.env['account.move.line'].create({
            'product_id': expense_product.id,
            'move_id': vendor_bill.id,
            'account_id': self.env['account.account'].search([('code', '=', '600000')]).id,
            'analytic_distribution': {project.account_id.id: 100},
            'price_unit': 20,
        })
        vendor_bill.action_post()  # An analytic line is created for the vendor bill move line
        self.assertEqual(project.account_id.vendor_bill_count, 1, 'Vendor bill should be linked to project account')
        self.assertTrue(vendor_bill.line_ids.analytic_line_ids, 'Analytic line should be created for the account move line')
        self.assertTrue(sale_order.order_line.analytic_line_ids, 'Analytic line should be linked to the sale order line created by the re-invoiced expense product')

        # Only the original vendor bill amount should appear on the project update, to stay consistent with the corresponding hr_expense behavior
        updates = project._get_profitability_items()
        data_line = updates['costs']['data'][0]
        self.assertEqual(data_line['id'], 'other_purchase_costs')
        self.assertEqual(data_line['billed'], -20)
        self.assertEqual(updates['costs']['total']['billed'], -20, 'Only the vendor bill should be deducted')
