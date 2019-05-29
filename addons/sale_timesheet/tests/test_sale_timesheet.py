# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tools import float_is_zero
from odoo.exceptions import UserError

from odoo.addons.sale_timesheet.tests.common import TestCommonSaleTimesheetNoChart


class TestSaleTimesheet(TestCommonSaleTimesheetNoChart):
    """ This test suite provide tests for the 3 main flows of selling services:
            - Selling services based on ordered quantities
            - Selling timesheet based on delivered quantities
            - Selling milestones, based on manual delivered quantities
        For that, we check the task/project created, the invoiced amounts, the delivered
        quantities changes,  ...
    """

    @classmethod
    def setUpClass(cls):
        super(TestSaleTimesheet, cls).setUpClass()
        # set up
        cls.setUpEmployees()
        cls.setUpServiceProducts()

    def test_timesheet_order(self):
        """ Test timesheet invoicing with 'invoice on order' timetracked products
                1. create SO with 2 ordered product and confirm
                2. create invoice
                3. log timesheet
                4. add new SO line (ordered service)
                5. create new invoice
        """
        # create SO and confirm it
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_customer_usd.id,
            'partner_invoice_id': self.partner_customer_usd.id,
            'partner_shipping_id': self.partner_customer_usd.id,
            'pricelist_id': self.pricelist_usd.id,
        })
        so_line_ordered_project_only = self.env['sale.order.line'].create({
            'name': self.product_order_timesheet4.name,
            'product_id': self.product_order_timesheet4.id,
            'product_uom_qty': 10,
            'product_uom': self.product_order_timesheet4.uom_id.id,
            'price_unit': self.product_order_timesheet4.list_price,
            'order_id': sale_order.id,
        })
        so_line_ordered_global_project = self.env['sale.order.line'].create({
            'name': self.product_order_timesheet2.name,
            'product_id': self.product_order_timesheet2.id,
            'product_uom_qty': 50,
            'product_uom': self.product_order_timesheet2.uom_id.id,
            'price_unit': self.product_order_timesheet2.list_price,
            'order_id': sale_order.id,
        })
        so_line_ordered_project_only.product_id_change()
        so_line_ordered_global_project.product_id_change()
        sale_order.action_confirm()
        task_serv2 = self.env['project.task'].search([('sale_line_id', '=', so_line_ordered_global_project.id)])
        project_serv1 = self.env['project.project'].search([('sale_line_id', '=', so_line_ordered_project_only.id)])

        self.assertEqual(sale_order.tasks_count, 1, "One task should have been created on SO confirmation")
        self.assertEqual(len(sale_order.project_ids), 2, "One project should have been created by the SO, when confirmed + the one from SO line 2 'task in global project'")
        self.assertEqual(sale_order.analytic_account_id, project_serv1.analytic_account_id, "The created project should be linked to the analytic account of the SO")

        # create invoice
        invoice1 = sale_order._create_invoices()[0]

        # let's log some timesheets (on the project created by so_line_ordered_project_only)
        timesheet1 = self.env['account.analytic.line'].create({
            'name': 'Test Line',
            'project_id': task_serv2.project_id.id,
            'task_id': task_serv2.id,
            'unit_amount': 10.5,
            'employee_id': self.employee_user.id,
        })
        self.assertEqual(so_line_ordered_global_project.qty_delivered, 10.5, 'Timesheet directly on project does not increase delivered quantity on so line')
        self.assertEqual(sale_order.invoice_status, 'invoiced', 'Sale Timesheet: "invoice on order" timesheets should not modify the invoice_status of the so')
        self.assertEqual(timesheet1.timesheet_invoice_type, 'billable_fixed', "Timesheets linked to SO line with ordered product shoulbe be billable fixed")
        self.assertFalse(timesheet1.timesheet_invoice_id, "The timesheet1 should not be linked to the invoice, since we are in ordered quantity")

        timesheet2 = self.env['account.analytic.line'].create({
            'name': 'Test Line',
            'project_id': task_serv2.project_id.id,
            'task_id': task_serv2.id,
            'unit_amount': 39.5,
            'employee_id': self.employee_user.id,
        })
        self.assertEqual(so_line_ordered_global_project.qty_delivered, 50, 'Sale Timesheet: timesheet does not increase delivered quantity on so line')
        self.assertEqual(sale_order.invoice_status, 'invoiced', 'Sale Timesheet: "invoice on order" timesheets should not modify the invoice_status of the so')
        self.assertEqual(timesheet2.timesheet_invoice_type, 'billable_fixed', "Timesheets linked to SO line with ordered product shoulbe be billable fixed")
        self.assertFalse(timesheet2.timesheet_invoice_id, "The timesheet should not be linked to the invoice, since we are in ordered quantity")

        timesheet3 = self.env['account.analytic.line'].create({
            'name': 'Test Line',
            'project_id': task_serv2.project_id.id,
            'unit_amount': 10,
            'employee_id': self.employee_user.id,
        })
        self.assertEqual(so_line_ordered_project_only.qty_delivered, 0.0, 'Timesheet directly on project does not increase delivered quantity on so line')
        self.assertEqual(timesheet3.timesheet_invoice_type, 'non_billable_project', "Timesheets without task shoulbe be 'no project found'")
        self.assertFalse(timesheet3.timesheet_invoice_id, "The timesheet should not be linked to the invoice, since we are in ordered quantity")

        # log timesheet on task in global project (higher than the initial ordrered qty)
        timesheet4 = self.env['account.analytic.line'].create({
            'name': 'Test Line',
            'project_id': task_serv2.project_id.id,
            'task_id': task_serv2.id,
            'unit_amount': 5,
            'employee_id': self.employee_user.id,
        })
        self.assertEqual(sale_order.invoice_status, 'upselling', 'Sale Timesheet: "invoice on order" timesheets should not modify the invoice_status of the so')
        self.assertFalse(timesheet4.timesheet_invoice_id, "The timesheet should not be linked to the invoice, since we are in ordered quantity")

        # add so line with produdct "create task in new project".
        so_line_ordered_task_in_project = self.env['sale.order.line'].create({
            'name': self.product_order_timesheet3.name,
            'product_id': self.product_order_timesheet3.id,
            'product_uom_qty': 3,
            'product_uom': self.product_order_timesheet3.uom_id.id,
            'price_unit': self.product_order_timesheet3.list_price,
            'order_id': sale_order.id,
        })

        self.assertEqual(sale_order.invoice_status, 'to invoice', 'Sale Timesheet: Adding a new service line (so line) should put the SO in "to invocie" state.')
        self.assertEqual(sale_order.tasks_count, 2, "Two tasks (1 per SO line) should have been created on SO confirmation")
        self.assertEqual(len(sale_order.project_ids), 2, "No new project should have been created by the SO, when selling 'new task in new project' product, since it reuse the one from 'project only'.")

        # get first invoice line of sale line linked to timesheet1
        invoice_line_1 = so_line_ordered_global_project.invoice_lines.filtered(lambda line: line.move_id == invoice1)

        self.assertEqual(so_line_ordered_global_project.product_uom_qty, invoice_line_1.quantity, "The invoice (ordered) quantity should not change when creating timesheet")

        # timesheet can be modified
        timesheet1.write({'unit_amount': 12})

        self.assertEqual(so_line_ordered_global_project.product_uom_qty, invoice_line_1.quantity, "The invoice (ordered) quantity should not change when modifying timesheet")

        # create second invoice
        invoice2 = sale_order._create_invoices()[0]

        self.assertEqual(len(sale_order.invoice_ids), 2, "A second invoice should have been created from the SO")
        self.assertTrue(float_is_zero(invoice2.amount_total - so_line_ordered_task_in_project.price_unit * 3, precision_digits=2), 'Sale: invoice generation on timesheets product is wrong')

        self.assertFalse(timesheet1.timesheet_invoice_id, "The timesheet1 should not be linked to the invoice, since we are in ordered quantity")
        self.assertFalse(timesheet2.timesheet_invoice_id, "The timesheet2 should not be linked to the invoice, since we are in ordered quantity")
        self.assertFalse(timesheet3.timesheet_invoice_id, "The timesheet3 should not be linked to the invoice, since we are in ordered quantity")
        self.assertFalse(timesheet4.timesheet_invoice_id, "The timesheet4 should not be linked to the invoice, since we are in ordered quantity")

        # validate the first invoice
        invoice1.post()

        self.assertEqual(so_line_ordered_global_project.product_uom_qty, invoice_line_1.quantity, "The invoice (ordered) quantity should not change when modifying timesheet")
        self.assertFalse(timesheet1.timesheet_invoice_id, "The timesheet1 should not be linked to the invoice, since we are in ordered quantity")
        self.assertFalse(timesheet2.timesheet_invoice_id, "The timesheet2 should not be linked to the invoice, since we are in ordered quantity")
        self.assertFalse(timesheet3.timesheet_invoice_id, "The timesheet3 should not be linked to the invoice, since we are in ordered quantity")
        self.assertFalse(timesheet4.timesheet_invoice_id, "The timesheet4 should not be linked to the invoice, since we are in ordered quantity")

        # timesheet can still be modified
        timesheet1.write({'unit_amount': 13})

    def test_timesheet_delivery(self):
        """ Test timesheet invoicing with 'invoice on delivery' timetracked products
                1. Create SO and confirm it
                2. log timesheet
                3. create invoice
                4. log other timesheet
                5. create a second invoice
                6. add new SO line (delivered service)
        """
        # create SO and confirm it
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_customer_usd.id,
            'partner_invoice_id': self.partner_customer_usd.id,
            'partner_shipping_id': self.partner_customer_usd.id,
            'pricelist_id': self.pricelist_usd.id,
        })
        so_line_deliver_global_project = self.env['sale.order.line'].create({
            'name': self.product_delivery_timesheet2.name,
            'product_id': self.product_delivery_timesheet2.id,
            'product_uom_qty': 50,
            'product_uom': self.product_delivery_timesheet2.uom_id.id,
            'price_unit': self.product_delivery_timesheet2.list_price,
            'order_id': sale_order.id,
        })
        so_line_deliver_task_project = self.env['sale.order.line'].create({
            'name': self.product_delivery_timesheet3.name,
            'product_id': self.product_delivery_timesheet3.id,
            'product_uom_qty': 20,
            'product_uom': self.product_delivery_timesheet3.uom_id.id,
            'price_unit': self.product_delivery_timesheet3.list_price,
            'order_id': sale_order.id,
        })
        so_line_deliver_global_project.product_id_change()
        so_line_deliver_task_project.product_id_change()

        # confirm SO
        sale_order.action_confirm()
        task_serv1 = self.env['project.task'].search([('sale_line_id', '=', so_line_deliver_global_project.id)])
        task_serv2 = self.env['project.task'].search([('sale_line_id', '=', so_line_deliver_task_project.id)])
        project_serv2 = self.env['project.project'].search([('sale_line_id', '=', so_line_deliver_task_project.id)])

        self.assertEqual(task_serv1.project_id, self.project_global, "Sale Timesheet: task should be created in global project")
        self.assertTrue(task_serv1, "Sale Timesheet: on SO confirmation, a task should have been created in global project")
        self.assertTrue(task_serv2, "Sale Timesheet: on SO confirmation, a task should have been created in a new project")
        self.assertEqual(sale_order.invoice_status, 'no', 'Sale Timesheet: "invoice on delivery" should not need to be invoiced on so confirmation')
        self.assertEqual(sale_order.analytic_account_id, task_serv2.project_id.analytic_account_id, "SO should have create a project")
        self.assertEqual(sale_order.tasks_count, 2, "Two tasks (1 per SO line) should have been created on SO confirmation")
        self.assertEqual(len(sale_order.project_ids), 2, "One project should have been created by the SO, when confirmed + the one from SO line 1 'task in global project'")
        self.assertEqual(sale_order.analytic_account_id, project_serv2.analytic_account_id, "The created project should be linked to the analytic account of the SO")

        # let's log some timesheets
        timesheet1 = self.env['account.analytic.line'].create({
            'name': 'Test Line',
            'project_id': task_serv1.project_id.id,  # global project
            'task_id': task_serv1.id,
            'unit_amount': 10.5,
            'employee_id': self.employee_manager.id,
        })
        self.assertEqual(so_line_deliver_global_project.invoice_status, 'to invoice', 'Sale Timesheet: "invoice on delivery" timesheets should set the so line in "to invoice" status when logged')
        self.assertEqual(so_line_deliver_task_project.invoice_status, 'no', 'Sale Timesheet: so line invoice status should not change when no timesheet linked to the line')
        self.assertEqual(sale_order.invoice_status, 'to invoice', 'Sale Timesheet: "invoice on delivery" timesheets should set the so in "to invoice" status when logged')
        self.assertEqual(timesheet1.timesheet_invoice_type, 'billable_time', "Timesheets linked to SO line with delivered product shoulbe be billable time")
        self.assertFalse(timesheet1.timesheet_invoice_id, "The timesheet1 should not be linked to the invoice yet")

        # invoice SO
        invoice1 = sale_order._create_invoices()
        self.assertTrue(float_is_zero(invoice1.amount_total - so_line_deliver_global_project.price_unit * 10.5, precision_digits=2), 'Sale: invoice generation on timesheets product is wrong')
        self.assertEqual(timesheet1.timesheet_invoice_id, invoice1, "The timesheet1 should not be linked to the invoice 1, as we are in delivered quantity (even if invoice is in draft")
        with self.assertRaises(UserError):  # We can not modify timesheet linked to invoice (even draft ones)
            timesheet1.write({'unit_amount': 42})

        # log some timesheets again
        timesheet2 = self.env['account.analytic.line'].create({
            'name': 'Test Line',
            'project_id': task_serv1.project_id.id,  # global project
            'task_id': task_serv1.id,
            'unit_amount': 39.5,
            'employee_id': self.employee_user.id,
        })
        self.assertEqual(so_line_deliver_global_project.invoice_status, 'to invoice', 'Sale Timesheet: "invoice on delivery" timesheets should set the so line in "to invoice" status when logged')
        self.assertEqual(so_line_deliver_task_project.invoice_status, 'no', 'Sale Timesheet: so line invoice status should not change when no timesheet linked to the line')
        self.assertEqual(sale_order.invoice_status, 'to invoice', 'Sale Timesheet: "invoice on delivery" timesheets should not modify the invoice_status of the so')
        self.assertEqual(timesheet2.timesheet_invoice_type, 'billable_time', "Timesheets linked to SO line with delivered product shoulbe be billable time")
        self.assertFalse(timesheet2.timesheet_invoice_id, "The timesheet2 should not be linked to the invoice yet")

        # create a second invoice
        invoice2 = sale_order._create_invoices()[0]
        self.assertEqual(len(sale_order.invoice_ids), 2, "A second invoice should have been created from the SO")
        self.assertEqual(so_line_deliver_global_project.invoice_status, 'invoiced', 'Sale Timesheet: "invoice on delivery" timesheets should set the so line in "to invoice" status when logged')
        self.assertEqual(sale_order.invoice_status, 'no', 'Sale Timesheet: "invoice on delivery" timesheets should be invoiced completely by now')
        self.assertEqual(timesheet2.timesheet_invoice_id, invoice2, "The timesheet2 should not be linked to the invoice 2")
        with self.assertRaises(UserError):  # We can not modify timesheet linked to invoice (even draft ones)
            timesheet2.write({'unit_amount': 42})

        # add a line on SO
        so_line_deliver_only_project = self.env['sale.order.line'].create({
            'name': self.product_delivery_timesheet4.name,
            'product_id': self.product_delivery_timesheet4.id,
            'product_uom_qty': 5,
            'product_uom': self.product_delivery_timesheet4.uom_id.id,
            'price_unit': self.product_delivery_timesheet4.list_price,
            'order_id': sale_order.id,
        })
        self.assertEqual(len(sale_order.project_ids), 2, "No new project should have been created by the SO, when selling 'project only' product, since it reuse the one from 'new task in new project'.")

        # let's log some timesheets on the project
        timesheet3 = self.env['account.analytic.line'].create({
            'name': 'Test Line',
            'project_id': project_serv2.id,
            'unit_amount': 7,
            'employee_id': self.employee_user.id,
        })
        self.assertTrue(float_is_zero(so_line_deliver_only_project.qty_delivered, precision_digits=2), "Timesheeting on project should not incremented the delivered quantity on the SO line")
        self.assertEqual(sale_order.invoice_status, 'no', 'Sale Timesheet: "invoice on delivery" timesheets should be invoiced completely by now')
        self.assertEqual(timesheet3.timesheet_invoice_type, 'non_billable_project', "Timesheets without task shoulbe be 'no project found'")
        self.assertFalse(timesheet3.timesheet_invoice_id, "The timesheet3 should not be linked to the invoice yet")

        # let's log some timesheets on the task (new task/new project)
        timesheet4 = self.env['account.analytic.line'].create({
            'name': 'Test Line 4',
            'project_id': task_serv2.project_id.id,
            'task_id': task_serv2.id,
            'unit_amount': 7,
            'employee_id': self.employee_user.id,
        })
        self.assertFalse(timesheet4.timesheet_invoice_id, "The timesheet4 should not be linked to the invoice yet")

        # modify a non invoiced timesheet
        timesheet4.write({'unit_amount': 42})

        self.assertFalse(timesheet4.timesheet_invoice_id, "The timesheet4 should not still be linked to the invoice")

        # validate the second invoice
        invoice2.post()

        self.assertEqual(timesheet1.timesheet_invoice_id, invoice1, "The timesheet1 should not be linked to the invoice 1, even after validation")
        self.assertEqual(timesheet2.timesheet_invoice_id, invoice2, "The timesheet2 should not be linked to the invoice 1, even after validation")
        self.assertFalse(timesheet3.timesheet_invoice_id, "The timesheet3 should not be linked to the invoice, since we are in ordered quantity")
        self.assertFalse(timesheet4.timesheet_invoice_id, "The timesheet4 should not be linked to the invoice, since we are in ordered quantity")

    def test_timesheet_manual(self):
        """ Test timesheet invoicing with 'invoice on delivery' timetracked products
        """
        # create SO and confirm it
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_customer_usd.id,
            'partner_invoice_id': self.partner_customer_usd.id,
            'partner_shipping_id': self.partner_customer_usd.id,
            'pricelist_id': self.pricelist_usd.id,
        })
        so_line_manual_global_project = self.env['sale.order.line'].create({
            'name': self.product_delivery_manual2.name,
            'product_id': self.product_delivery_manual2.id,
            'product_uom_qty': 50,
            'product_uom': self.product_delivery_manual2.uom_id.id,
            'price_unit': self.product_delivery_manual2.list_price,
            'order_id': sale_order.id,
        })
        so_line_manual_only_project = self.env['sale.order.line'].create({
            'name': self.product_delivery_manual4.name,
            'product_id': self.product_delivery_manual4.id,
            'product_uom_qty': 20,
            'product_uom': self.product_delivery_manual4.uom_id.id,
            'price_unit': self.product_delivery_manual4.list_price,
            'order_id': sale_order.id,
        })

        # confirm SO
        sale_order.action_confirm()
        self.assertTrue(sale_order.project_ids, "Sales Order should have create a project")
        self.assertEqual(sale_order.invoice_status, 'no', 'Sale Timesheet: manually product should not need to be invoiced on so confirmation')

        project_serv2 = so_line_manual_only_project.project_id
        self.assertTrue(project_serv2, "A second project is created when selling 'project only' after SO confirmation.")
        self.assertEqual(sale_order.analytic_account_id, project_serv2.analytic_account_id, "The created project should be linked to the analytic account of the SO")

        # let's log some timesheets (on task and project)
        timesheet1 = self.env['account.analytic.line'].create({
            'name': 'Test Line',
            'project_id': self.project_global.id,  # global project
            'task_id': so_line_manual_global_project.task_id.id,
            'unit_amount': 6,
            'employee_id': self.employee_manager.id,
        })

        timesheet2 = self.env['account.analytic.line'].create({
            'name': 'Test Line',
            'project_id': self.project_global.id,  # global project
            'unit_amount': 3,
            'employee_id': self.employee_manager.id,
        })

        self.assertEqual(len(sale_order.project_ids), 2, "One project should have been created by the SO, when confirmed + the one coming from SO line 1 'task in global project'.")
        self.assertEqual(so_line_manual_global_project.task_id.sale_line_id, so_line_manual_global_project, "Task from a milestone product should be linked to its SO line too")
        self.assertEqual(timesheet1.timesheet_invoice_type, 'billable_fixed', "Milestone timesheet goes in billable fixed category")
        self.assertTrue(float_is_zero(so_line_manual_global_project.qty_delivered, precision_digits=2), "Milestone Timesheeting should not incremented the delivered quantity on the SO line")
        self.assertEqual(so_line_manual_global_project.qty_to_invoice, 0.0, "Manual service should not be affected by timesheet on their created task.")
        self.assertEqual(so_line_manual_only_project.qty_to_invoice, 0.0, "Manual service should not be affected by timesheet on their created project.")
        self.assertEqual(sale_order.invoice_status, 'no', 'Sale Timesheet: "invoice on delivery" should not need to be invoiced on so confirmation')

        self.assertEqual(timesheet1.timesheet_invoice_type, 'billable_fixed', "Timesheets linked to SO line with ordered product shoulbe be billable fixed since it is a milestone")
        self.assertEqual(timesheet2.timesheet_invoice_type, 'non_billable_project', "Timesheets without task shoulbe be 'no project found'")
        self.assertFalse(timesheet1.timesheet_invoice_id, "The timesheet1 should not be linked to the invoice")
        self.assertFalse(timesheet2.timesheet_invoice_id, "The timesheet2 should not be linked to the invoice")

        # invoice SO
        sale_order.order_line.write({'qty_delivered': 5})
        invoice1 = sale_order._create_invoices()

        for invoice_line in invoice1.invoice_line_ids:
            self.assertEqual(invoice_line.quantity, 5, "The invoiced quantity should be 5, as manually set on SO lines")

        self.assertFalse(timesheet1.timesheet_invoice_id, "The timesheet1 should not be linked to the invoice, since timesheets are used for time tracking in milestone")
        self.assertFalse(timesheet2.timesheet_invoice_id, "The timesheet2 should not be linked to the invoice, since timesheets are used for time tracking in milestone")

        # validate the invoice
        invoice1.post()

        self.assertFalse(timesheet1.timesheet_invoice_id, "The timesheet1 should not be linked to the invoice, even after invoice validation")
        self.assertFalse(timesheet2.timesheet_invoice_id, "The timesheet2 should not be linked to the invoice, even after invoice validation")
