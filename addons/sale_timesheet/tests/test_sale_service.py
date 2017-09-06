# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.sale.tests.test_sale_common import TestSale


class TestSaleService(TestSale):

    def test_sale_service(self):
        """ Test task creation when confirming a so with the corresponding product """
        prod_task = self.env.ref('product.product_product_1')
        so_vals = {
            'partner_id': self.partner.id,
            'partner_invoice_id': self.partner.id,
            'partner_shipping_id': self.partner.id,
            'order_line': [(0, 0, {'name': prod_task.name, 'product_id': prod_task.id, 'product_uom_qty': 50, 'product_uom': prod_task.uom_id.id, 'price_unit': prod_task.list_price})],
            'pricelist_id': self.env.ref('product.list0').id,
        }
        so = self.env['sale.order'].create(so_vals)
        so.action_confirm()
        self.assertEqual(so.invoice_status, 'no', 'Sale Service: there should be nothing to invoice after validation')

        # check task creation
        project = self.env.ref('sale_timesheet.project_GAP')
        task = project.task_ids.filtered(lambda t: t.name == '%s:%s' % (so.name, prod_task.name))
        self.assertTrue(task, 'Sale Service: task is not created')
        self.assertEqual(task.partner_id, so.partner_id, 'Sale Service: customer should be the same on task and on SO')
        # register timesheet on task
        self.env['account.analytic.line'].create({
            'name': 'Test Line',
            'project_id': project.id,
            'task_id': task.id,
            'unit_amount': 50,
            'user_id': self.manager.id,
        })
        self.assertEqual(so.invoice_status, 'to invoice', 'Sale Service: there should be something to invoice after registering timesheets')
        so.action_invoice_create()
        line = so.order_line
        self.assertTrue(line.product_uom_qty == line.qty_delivered == line.qty_invoiced, 'Sale Service: line should be invoiced completely')
        self.assertEqual(so.invoice_status, 'invoiced', 'Sale Service: SO should be invoiced')
        self.assertEqual(so.tasks_count, 1, "A task should have been created on SO confirmation.")

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
            'track_service': 'task',
            'project_id': project.id
        })

        self.env['sale.order.line'].create({
            'name': product_service_task.name,
            'product_id': product_service_task.id,
            'product_uom_qty': 10,
            'product_uom': product_service_task.uom_id.id,
            'price_unit': product_service_task.list_price,
            'order_id': so.id,
        })

        self.assertEqual(so.tasks_count, 2, "Adding a new service line on a confirmer SO should create a new task.")
