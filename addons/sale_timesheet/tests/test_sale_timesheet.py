# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tools import float_is_zero, float_compare

from odoo.addons.sale_timesheet.tests.common import CommonTest


class TestSaleTimesheet(CommonTest):
    """ This test suite provide tests for the 3 main flows of selling services:
            - Selling services based on ordered quantities
            - Selling timesheet based on delivered quantities
            - Selling milestones, based on manual delivered quantities
        For that, we check the task/project created, the invoiced amounts, the delivered
        quantities changes,  ...
    """

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
            'partner_id': self.partner_usd.id,
            'partner_invoice_id': self.partner_usd.id,
            'partner_shipping_id': self.partner_usd.id,
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

        self.assertEqual(sale_order.tasks_count, 1, "One task should have been created on SO confirmation")
        self.assertTrue(sale_order.project_project_id, "A project should have been created by the SO, when confirmed.")

        # create invoice
        sale_order.action_invoice_create()

        # let's log some timesheets (on the project created by so_line_ordered_project_only)
        self.env['account.analytic.line'].create({
            'name': 'Test Line',
            'project_id': sale_order.project_project_id.id,
            'task_id': task_serv2.id,
            'unit_amount': 10.5,
            'employee_id': self.employee_user.id,
        })
        self.assertEqual(so_line_ordered_global_project.qty_delivered, 10.5, 'Timesheet directly on project does not increase delivered quantity on so line')
        self.assertEqual(sale_order.invoice_status, 'invoiced', 'Sale Timesheet: "invoice on order" timesheets should not modify the invoice_status of the so')

        self.env['account.analytic.line'].create({
            'name': 'Test Line',
            'project_id': sale_order.project_project_id.id,
            'task_id': task_serv2.id,
            'unit_amount': 39.5,
            'employee_id': self.employee_user.id,
        })
        self.assertEqual(so_line_ordered_global_project.qty_delivered, 50, 'Sale Timesheet: timesheet does not increase delivered quantity on so line')
        self.assertEqual(sale_order.invoice_status, 'invoiced', 'Sale Timesheet: "invoice on order" timesheets should not modify the invoice_status of the so')

        self.env['account.analytic.line'].create({
            'name': 'Test Line',
            'project_id': sale_order.project_project_id.id,
            'unit_amount': 10,
            'employee_id': self.employee_user.id,
        })
        self.assertEqual(so_line_ordered_project_only.qty_delivered, 0.0, 'Timesheet directly on project does not increase delivered quantity on so line')

        # log timesheet on task in global project (higher than the initial ordrered qty)
        self.env['account.analytic.line'].create({
            'name': 'Test Line',
            'project_id': sale_order.project_project_id.id,
            'task_id': task_serv2.id,
            'unit_amount': 5,
            'employee_id': self.employee_user.id,
        })
        self.assertEqual(sale_order.invoice_status, 'upselling', 'Sale Timesheet: "invoice on order" timesheets should not modify the invoice_status of the so')

        # add so line with produdct "create task in new project". (project will be the one from SO)
        so_line_ordered_task_new_project = self.env['sale.order.line'].create({
            'name': self.product_order_timesheet3.name,
            'product_id': self.product_order_timesheet3.id,
            'product_uom_qty': 3,
            'product_uom': self.product_order_timesheet3.uom_id.id,
            'price_unit': self.product_order_timesheet3.list_price,
            'order_id': sale_order.id,
        })
        task_serv3 = self.env['project.task'].search([('sale_line_id', '=', so_line_ordered_task_new_project.id)])
        self.assertEqual(sale_order.invoice_status, 'to invoice', 'Sale Timesheet: Adding a new service line (so line) should put the SO in "to invocie" state.')
        self.assertEqual(sale_order.tasks_count, 2, "Two tasks (1 per SO line) should have been created on SO confirmation")

        # create invoice
        invoice_id = sale_order.action_invoice_create()
        invoice = self.env['account.invoice'].browse(invoice_id)
        self.assertEqual(len(sale_order.invoice_ids), 2, "A second invoice should have been created from the SO")
        self.assertTrue(float_is_zero(invoice.amount_total - so_line_ordered_task_new_project.price_unit * 3, precision_digits=2), 'Sale: invoice generation on timesheets product is wrong')
        self.assertEqual(sale_order.project_project_id, task_serv3.project_id, "When creating task in new project, the task should be in SO project (if already exists), otherwise it created one.")

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
            'partner_id': self.partner_usd.id,
            'partner_invoice_id': self.partner_usd.id,
            'partner_shipping_id': self.partner_usd.id,
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
        task_serv2 = self.env['project.task'].search([('sale_line_id', '=', so_line_deliver_global_project.id)])
        task_serv3 = self.env['project.task'].search([('sale_line_id', '=', so_line_deliver_task_project.id)])

        self.assertEqual(task_serv2.project_id, self.project_global, "Sale Timesheet: task should be created in global project")
        self.assertTrue(task_serv2, "Sale Timesheet: on SO confirmation, a task should have been created in global project")
        self.assertTrue(task_serv3, "Sale Timesheet: on SO confirmation, a task should have been created in a new project")
        self.assertEqual(sale_order.invoice_status, 'no', 'Sale Timesheet: "invoice on delivery" should not need to be invoiced on so confirmation')
        self.assertEqual(sale_order.analytic_account_id, task_serv3.project_id.analytic_account_id, "SO should have create a project")
        self.assertEqual(sale_order.tasks_count, 2, "Two tasks (1 per SO line) should have been created on SO confirmation")

        # let's log some timesheets
        self.env['account.analytic.line'].create({
            'name': 'Test Line',
            'project_id': task_serv2.project_id.id,  # global project
            'task_id': task_serv2.id,
            'unit_amount': 10.5,
            'employee_id': self.employee_manager.id,
        })
        self.assertEqual(so_line_deliver_global_project.invoice_status, 'to invoice', 'Sale Timesheet: "invoice on delivery" timesheets should set the so line in "to invoice" status when logged')
        self.assertEqual(so_line_deliver_task_project.invoice_status, 'no', 'Sale Timesheet: so line invoice status should not change when no timesheet linked to the line')
        self.assertEqual(sale_order.invoice_status, 'to invoice', 'Sale Timesheet: "invoice on delivery" timesheets should set the so in "to invoice" status when logged')

        # invoice SO
        invoice_id = sale_order.action_invoice_create()
        invoice = self.env['account.invoice'].browse(invoice_id)
        self.assertTrue(float_is_zero(invoice.amount_total - so_line_deliver_global_project.price_unit * 10.5, precision_digits=2), 'Sale: invoice generation on timesheets product is wrong')

        # log some timesheets again
        self.env['account.analytic.line'].create({
            'name': 'Test Line',
            'project_id': task_serv2.project_id.id,  # global project
            'task_id': task_serv2.id,
            'unit_amount': 39.5,
            'employee_id': self.employee_user.id,
        })
        self.assertEqual(so_line_deliver_global_project.invoice_status, 'to invoice', 'Sale Timesheet: "invoice on delivery" timesheets should set the so line in "to invoice" status when logged')
        self.assertEqual(so_line_deliver_task_project.invoice_status, 'no', 'Sale Timesheet: so line invoice status should not change when no timesheet linked to the line')
        self.assertEqual(sale_order.invoice_status, 'to invoice', 'Sale Timesheet: "invoice on delivery" timesheets should not modify the invoice_status of the so')

        # create a second invoice
        sale_order.action_invoice_create()
        self.assertEqual(so_line_deliver_global_project.invoice_status, 'invoiced', 'Sale Timesheet: "invoice on delivery" timesheets should set the so line in "to invoice" status when logged')
        self.assertEqual(sale_order.invoice_status, 'no', 'Sale Timesheet: "invoice on delivery" timesheets should be invoiced completely by now')

        # add a line on SO
        so_line_deliver_only_project = self.env['sale.order.line'].create({
            'name': self.product_delivery_timesheet4.name,
            'product_id': self.product_delivery_timesheet4.id,
            'product_uom_qty': 5,
            'product_uom': self.product_delivery_timesheet4.uom_id.id,
            'price_unit': self.product_delivery_timesheet4.list_price,
            'order_id': sale_order.id,
        })
        self.assertEqual(sale_order.project_project_id, task_serv3.project_id, "SO should not have create a second project, since so line 3 already create one project for the SO")

        # let's log some timesheets on the project
        self.env['account.analytic.line'].create({
            'name': 'Test Line',
            'project_id': sale_order.project_project_id.id,  # global project
            'unit_amount': 7,
            'employee_id': self.employee_user.id,
        })
        self.assertTrue(float_is_zero(so_line_deliver_only_project.qty_delivered, precision_digits=2), "Timesheeting on project should not incremented the delivered quantity on the SO line")
        self.assertEqual(sale_order.invoice_status, 'no', 'Sale Timesheet: "invoice on delivery" timesheets should be invoiced completely by now')

    def test_timesheet_manual(self):
        """ Test timesheet invoicing with 'invoice on delivery' timetracked products
        """
        # create SO and confirm it
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_usd.id,
            'partner_invoice_id': self.partner_usd.id,
            'partner_shipping_id': self.partner_usd.id,
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
        self.assertTrue(sale_order.project_project_id, "Sales Order should have create a project")
        self.assertEqual(sale_order.invoice_status, 'no', 'Sale Timesheet: manually product should not need to be invoiced on so confirmation')

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
            'project_id': sale_order.project_project_id.id,  # global project
            'unit_amount': 3,
            'employee_id': self.employee_manager.id,
        })

        self.assertEqual(so_line_manual_global_project.task_id.sale_line_id, so_line_manual_global_project, "Task from a milestone product should be linked to its SO line too")
        self.assertEqual(timesheet1.timesheet_invoice_type, 'billable_fixed', "Milestone timesheet goes in billable fixed category")
        self.assertTrue(float_is_zero(so_line_manual_global_project.qty_delivered, precision_digits=2), "Milestone Timesheeting should not incremented the delivered quantity on the SO line")
        self.assertEqual(so_line_manual_global_project.qty_to_invoice, 0.0, "Manual service should not be affected by timesheet on their created task.")
        self.assertEqual(so_line_manual_only_project.qty_to_invoice, 0.0, "Manual service should not be affected by timesheet on their created project.")
        self.assertEqual(sale_order.invoice_status, 'no', 'Sale Timesheet: "invoice on delivery" should not need to be invoiced on so confirmation')
