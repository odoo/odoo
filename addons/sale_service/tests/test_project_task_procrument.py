# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.tests import common
from datetime import datetime


class TestProjectTaskProcrument(common.TransactionCase):

    def setUp(self):
        super(TestProjectTaskProcrument, self).setUp()
        self.Product = self.env['product.product']
        self.SaleOrder = self.env['sale.order']
        self.SaleOrderLine = self.env['sale.order.line']
        self.ProcurementOrder = self.env['procurement.order']
        self.ProjectTask = self.env['project.task']
        self.uom = self.env.ref('product.product_uom_day')
        self.partner = self.env.ref('base.res_partner_2')
        self.pricelist = self.env.ref('product.list0')
        self.project_stage = self.env.ref('project.project_stage_2')

    def test_00_procrument(self):

        # Update product to automatically create tasks
        self.auto_task_service = self.Product.create({
            'auto_create_task': True,
            'name': 'Advanced auto task Service',
            'type': 'service',
            'list_price': 150.0,
            'standard_price': 100.0,
            'uom_id': self.uom.id,
            'uom_po_id': self.uom.id
        })

        # Create a new sales order with a service product
        self.sale_order_service = self.SaleOrder.create({
            'partner_id': self.partner.id,
            'pricelist_id': self.pricelist.id
        })

        # Associate a sale order line
        self.service_line = self.SaleOrderLine.create({
            'product_id': self.auto_task_service.id,
            'product_uom_qty': 50.0,
            'name': 'Fixing the bugs',
            'order_id': self.sale_order_service.id
        })

        # In order to test process to generate task automatic from procurement, I confirm sale order to sale service product.
        self.sale_order_service.signal_workflow('order_confirm')

        # I run the scheduler.
        self.ProcurementOrder.run_scheduler()

        # Now I check the details of the generated task
        procurement = self.ProcurementOrder.search([('sale_line_id', '=', self.service_line.id)], limit=1)
        self.assertTrue(procurement, "Procurement is not generated for Service Order Line.")
        self.assertNotEqual(procurement.state, "done", "Task is not generated.")
        task = procurement.task_id
        self.assertTrue(task, "Task is not generated.")
        # check whether task project either is the product's project, or corresponds to the analytic account of sale order
        project = task.project_id
        if procurement.product_id.project_id:
            self.assertEqual(project, procurement.product_id.project_id, "Project does not correspond.")
        elif procurement.sale_line_id:
            account = procurement.sale_line_id.order_id.project_id
            if project and account:
                self.assertEqual(project.analytic_account_id, account, "Project does not correspond.")
        planned_hours = procurement._convert_qty_company_hours()
        self.assertEqual(task.planned_hours, planned_hours, "Planned Hours do not correspond.")
        self.assertEqual(datetime.strptime(task.date_deadline, '%Y-%m-%d'), datetime.strptime(procurement.date_planned[:10], '%Y-%m-%d'), "Deadline does not correspond.")
        if procurement.product_id.product_manager:
            self.assertEqual(task.user_id.id, procurement.product_id.product_manager.id, "Allocated Person does not correspond with Service Product Manager.")

        # I close that task.
        tasks = self.ProjectTask.search([('sale_line_id', '=', self.service_line.id)])
        self.assertTrue(tasks, "Task is not generated for Service Order Line.")
        tasks.stage_id = self.project_stage.id

        # I check procurement of Service Order Line after closed task.
        procurement = self.ProcurementOrder.search([('sale_line_id', '=', self.service_line.id)], limit=1)
        self.assertTrue(procurement, "Procurement is not generated for Service Order Line.")
        self.assertEqual(procurement.state, 'done', "Procurement should be closed.")
