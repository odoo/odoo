# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.sale_timesheet.tests.common import CommonTest
from odoo.exceptions import UserError


class TestSaleService(CommonTest):
    """ This test suite provide checks for miscellaneous small things. """

    def test_sale_service(self):
        """ Test task creation when confirming a sale_order with the corresponding product """
        sale_order_vals = {
            'partner_id': self.partner_usd.id,
            'partner_invoice_id': self.partner_usd.id,
            'partner_shipping_id': self.partner_usd.id,
            'order_line': [(0, 0, {
                'name': self.product_delivery_timesheet2.name,
                'product_id': self.product_delivery_timesheet2.id,
                'product_uom_qty': 50,
                'product_uom': self.product_delivery_timesheet2.uom_id.id,
                'price_unit': self.product_delivery_timesheet2.list_price
                }),
            ],
            'pricelist_id': self.pricelist_usd.id,
        }
        sale_order = self.env['sale.order'].create(sale_order_vals)
        sale_order.order_line._compute_product_updatable()
        self.assertTrue(sale_order.order_line[0].product_updatable)
        sale_order.action_confirm()
        sale_order.order_line._compute_product_updatable()
        self.assertFalse(sale_order.order_line[0].product_updatable)
        self.assertEqual(sale_order.invoice_status, 'no', 'Sale Service: there should be nothing to invoice after validation')

        # check task creation
        project = self.project_global
        task = project.task_ids.filtered(lambda t: t.name == '%s:%s' % (sale_order.name, self.product_delivery_timesheet2.name))
        self.assertTrue(task, 'Sale Service: task is not created')
        self.assertEqual(task.partner_id, sale_order.partner_id, 'Sale Service: customer should be the same on task and on SO')
        self.assertEqual(task.email_from, sale_order.partner_id.email, 'Sale Service: Task Email should be the same as the SO customer Email')
        # register timesheet on task
        self.env['account.analytic.line'].create({
            'name': 'Test Line',
            'project_id': project.id,
            'task_id': task.id,
            'unit_amount': 50,
            'employee_id': self.employee_manager.id,
        })
        self.assertEqual(sale_order.invoice_status, 'to invoice', 'Sale Service: there should be sale_ordermething to invoice after registering timesheets')
        sale_order.action_invoice_create()
        line = sale_order.order_line
        self.assertTrue(line.product_uom_qty == line.qty_delivered == line.qty_invoiced, 'Sale Service: line should be invoiced completely')
        self.assertEqual(sale_order.invoice_status, 'invoiced', 'Sale Service: SO should be invoiced')
        self.assertEqual(sale_order.tasks_count, 1, "A task should have been created on SO confirmation.")

        # Add a line on the confirmed SO, and it should generate a new task directly
        product_service_task = self.env['product.product'].create({
            'name': "Delivered Service",
            'standard_price': 30,
            'list_price': 90,
            'type': 'service',
            'invoice_policy': 'delivery',
            'uom_id': self.env.ref('product.product_uom_hour').id,
            'uom_po_id': self.env.ref('product.product_uom_hour').id,
            'default_code': 'SERV-DELI',
            'service_type': 'timesheet',
            'service_tracking': 'task_global_project',
            'project_id': project.id
        })

        self.env['sale.order.line'].create({
            'name': product_service_task.name,
            'product_id': product_service_task.id,
            'product_uom_qty': 10,
            'product_uom': product_service_task.uom_id.id,
            'price_unit': product_service_task.list_price,
            'order_id': sale_order.id,
        })

        self.assertEqual(sale_order.tasks_count, 2, "Adding a new service line on a confirmer SO should create a new task.")

    def test_timesheet_uom(self):
        """ Test timesheet invoicing and uom conversion """
        # create SO and confirm it
        uom_days = self.env.ref('product.product_uom_day')
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_usd.id,
            'partner_invoice_id': self.partner_usd.id,
            'partner_shipping_id': self.partner_usd.id,
            'order_line': [
                (0, 0, {
                    'name': self.product_delivery_timesheet3.name,
                    'product_id': self.product_delivery_timesheet3.id,
                    'product_uom_qty': 5,
                    'product_uom': uom_days.id,
                    'price_unit': self.product_delivery_timesheet3.list_price
                })
            ],
            'pricelist_id': self.pricelist_usd.id,
        })
        sale_order.action_confirm()
        task = self.env['project.task'].search([('sale_line_id', '=', sale_order.order_line.id)])

        # let's log some timesheets
        self.env['account.analytic.line'].create({
            'name': 'Test Line',
            'project_id': sale_order.project_project_id.id,
            'task_id': task.id,
            'unit_amount': 16,
            'employee_id': self.employee_manager.id,
        })
        self.assertEqual(sale_order.order_line.qty_delivered, 2, 'Sale: uom conversion of timesheets is wrong')

        self.env['account.analytic.line'].create({
            'name': 'Test Line',
            'project_id': sale_order.project_project_id.id,
            'task_id': task.id,
            'unit_amount': 24,
            'employee_id': self.employee_user.id,
        })
        sale_order.action_invoice_create()
        self.assertEqual(sale_order.invoice_status, 'invoiced', 'Sale Timesheet: "invoice on delivery" timesheets should not modify the invoice_status of the so')

    def test_task_so_line_assignation(self):
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
            'product_uom_qty': 10,
            'product_uom': self.product_delivery_timesheet2.uom_id.id,
            'price_unit': self.product_delivery_timesheet2.list_price,
            'order_id': sale_order.id,
        })
        so_line_deliver_global_project.product_id_change()
        sale_order.action_confirm()
        task_serv2 = self.env['project.task'].search([('sale_line_id', '=', so_line_deliver_global_project.id)])

        # let's log some timesheets (on the project created by so_line_ordered_project_only)
        timesheets = self.env['account.analytic.line']
        timesheets |= self.env['account.analytic.line'].create({
            'name': 'Test Line',
            'project_id': task_serv2.project_id.id,
            'task_id': task_serv2.id,
            'unit_amount': 4,
            'employee_id': self.employee_user.id,
        })
        timesheets |= self.env['account.analytic.line'].create({
            'name': 'Test Line',
            'project_id': task_serv2.project_id.id,
            'task_id': task_serv2.id,
            'unit_amount': 1,
            'employee_id': self.employee_manager.id,
        })
        self.assertTrue(all([billing_type == 'billable_time' for billing_type in timesheets.mapped('timesheet_invoice_type')]), "All timesheets linked to the task should be on 'billable time'")
        self.assertEqual(so_line_deliver_global_project.qty_to_invoice, 5, "Quantity to invoice should have been increased when logging timesheet on delivered quantities task")

        # make task non billable
        task_serv2.write({'sale_line_id': False})
        self.assertTrue(all([billing_type == 'non_billable' for billing_type in timesheets.mapped('timesheet_invoice_type')]), "Timesheet to a non billable task should be non billable too")

        # make task billable again
        task_serv2.write({'sale_line_id': so_line_deliver_global_project.id})
        self.assertTrue(all([billing_type == 'billable_time' for billing_type in timesheets.mapped('timesheet_invoice_type')]), "Timesheet to a billable time task should be billable")

        # invoice SO, and validate invoice
        invoice_id = sale_order.action_invoice_create()[0]
        invoice = self.env['account.invoice'].browse(invoice_id)
        invoice.action_invoice_open()

        # try to update timesheets, catch error 'You cannot modify invoiced timesheet'
        with self.assertRaises(UserError):
            task_serv2.write({'sale_line_id': False})

    def test_delivered_quantity(self):
        # create SO and confirm it
        sale_order = self.env['sale.order'].with_context(tracking_disable=True).create({
            'partner_id': self.partner_usd.id,
            'partner_invoice_id': self.partner_usd.id,
            'partner_shipping_id': self.partner_usd.id,
            'pricelist_id': self.pricelist_usd.id,
        })
        so_line_deliver_new_task_project = self.env['sale.order.line'].create({
            'name': self.product_delivery_timesheet3.name,
            'product_id': self.product_delivery_timesheet3.id,
            'product_uom_qty': 10,
            'product_uom': self.product_delivery_timesheet3.uom_id.id,
            'price_unit': self.product_delivery_timesheet3.list_price,
            'order_id': sale_order.id,
        })
        so_line_deliver_new_task_project.product_id_change()
        sale_order.action_confirm()
        task_serv2 = self.env['project.task'].search([('sale_line_id', '=', so_line_deliver_new_task_project.id)])

        # add a timesheet
        timesheet1 = self.env['account.analytic.line'].create({
            'name': 'Test Line',
            'project_id': task_serv2.project_id.id,
            'task_id': task_serv2.id,
            'unit_amount': 4,
            'employee_id': self.employee_user.id,
        })
        self.assertEqual(so_line_deliver_new_task_project.qty_delivered, timesheet1.unit_amount, 'Delivered quantity should be the same then its only related timesheet.')

        # remove the only timesheet
        timesheet1.unlink()
        self.assertEqual(so_line_deliver_new_task_project.qty_delivered, 0.0, 'Delivered quantity should be reset to zero, since there is no more timesheet.')

        # log 2 new timesheets
        timesheet2 = self.env['account.analytic.line'].create({
            'name': 'Test Line 2',
            'project_id': task_serv2.project_id.id,
            'task_id': task_serv2.id,
            'unit_amount': 4,
            'employee_id': self.employee_user.id,
        })
        timesheet3 = self.env['account.analytic.line'].create({
            'name': 'Test Line 3',
            'project_id': task_serv2.project_id.id,
            'task_id': task_serv2.id,
            'unit_amount': 2,
            'employee_id': self.employee_user.id,
        })
        self.assertEqual(so_line_deliver_new_task_project.qty_delivered, timesheet2.unit_amount + timesheet3.unit_amount, 'Delivered quantity should be the sum of the 2 timesheets unit amounts.')

        # remove timesheet2
        timesheet2.unlink()
        self.assertEqual(so_line_deliver_new_task_project.qty_delivered, timesheet3.unit_amount, 'Delivered quantity should be reset to the sum of remaining timesheets unit amounts.')
