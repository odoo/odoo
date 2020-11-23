# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase


class TestSaleProject(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.analytic_account_sale = cls.env['account.analytic.account'].create({
            'name': 'Project for selling timesheet - AA',
            'code': 'AA-2030'
        })

        # Create projects
        cls.project_global = cls.env['project.project'].create({
            'name': 'Global Project',
            'analytic_account_id': cls.analytic_account_sale.id,
        })
        cls.project_template = cls.env['project.project'].create({
            'name': 'Project TEMPLATE for services',
        })
        cls.project_template_state = cls.env['project.task.type'].create({
            'name': 'Only stage in project template',
            'sequence': 1,
            'project_ids': [(4, cls.project_template.id)]
        })

        # Create service products
        uom_hour = cls.env.ref('uom.product_uom_hour')

        cls.product_order_service1 = cls.env['product.product'].create({
            'name': "Service Ordered, create no task",
            'standard_price': 11,
            'list_price': 13,
            'type': 'service',
            'invoice_policy': 'order',
            'uom_id': uom_hour.id,
            'uom_po_id': uom_hour.id,
            'default_code': 'SERV-ORDERED1',
            'service_tracking': 'no',
            'project_id': False,
        })
        cls.product_order_service2 = cls.env['product.product'].create({
            'name': "Service Ordered, create task in global project",
            'standard_price': 30,
            'list_price': 90,
            'type': 'service',
            'invoice_policy': 'order',
            'uom_id': uom_hour.id,
            'uom_po_id': uom_hour.id,
            'default_code': 'SERV-ORDERED2',
            'service_tracking': 'task_global_project',
            'project_id': cls.project_global.id,
        })
        cls.product_order_service3 = cls.env['product.product'].create({
            'name': "Service Ordered, create task in new project",
            'standard_price': 10,
            'list_price': 20,
            'type': 'service',
            'invoice_policy': 'order',
            'uom_id': uom_hour.id,
            'uom_po_id': uom_hour.id,
            'default_code': 'SERV-ORDERED3',
            'service_tracking': 'task_in_project',
            'project_id': False,  # will create a project
        })
        cls.product_order_service4 = cls.env['product.product'].create({
            'name': "Service Ordered, create project only",
            'standard_price': 15,
            'list_price': 30,
            'type': 'service',
            'invoice_policy': 'order',
            'uom_id': uom_hour.id,
            'uom_po_id': uom_hour.id,
            'default_code': 'SERV-ORDERED4',
            'service_tracking': 'project_only',
            'project_id': False,
        })

    def test_sale_order_with_project_task(self):
        SaleOrderLine = self.env['sale.order.line'].with_context(tracking_disable=True)

        partner = self.env['res.partner'].create({'name': "Mur en béton"})
        sale_order = self.env['sale.order'].with_context(tracking_disable=True).create({
            'partner_id': partner.id,
            'partner_invoice_id': partner.id,
            'partner_shipping_id': partner.id,
        })
        so_line_order_no_task = SaleOrderLine.create({
            'name': self.product_order_service1.name,
            'product_id': self.product_order_service1.id,
            'product_uom_qty': 10,
            'product_uom': self.product_order_service1.uom_id.id,
            'price_unit': self.product_order_service1.list_price,
            'order_id': sale_order.id,
        })

        so_line_order_task_in_global = SaleOrderLine.create({
            'name': self.product_order_service2.name,
            'product_id': self.product_order_service2.id,
            'product_uom_qty': 10,
            'product_uom': self.product_order_service2.uom_id.id,
            'price_unit': self.product_order_service2.list_price,
            'order_id': sale_order.id,
        })

        so_line_order_new_task_new_project = SaleOrderLine.create({
            'name': self.product_order_service3.name,
            'product_id': self.product_order_service3.id,
            'product_uom_qty': 10,
            'product_uom': self.product_order_service3.uom_id.id,
            'price_unit': self.product_order_service3.list_price,
            'order_id': sale_order.id,
        })

        so_line_order_only_project = SaleOrderLine.create({
            'name': self.product_order_service4.name,
            'product_id': self.product_order_service4.id,
            'product_uom_qty': 10,
            'product_uom': self.product_order_service4.uom_id.id,
            'price_unit': self.product_order_service4.list_price,
            'order_id': sale_order.id,
        })
        sale_order.action_confirm()

        # service_tracking 'no'
        self.assertFalse(so_line_order_no_task.project_id, "The project should not be linked to no task product")
        self.assertFalse(so_line_order_no_task.task_id, "The task should not be linked to no task product")
        # service_tracking 'task_global_project'
        self.assertFalse(so_line_order_task_in_global.project_id, "Only task should be created, project should not be linked")
        self.assertEqual(self.project_global.tasks.sale_line_id, so_line_order_task_in_global, "Global project's task should be linked to so line")
        #  service_tracking 'task_in_project'
        self.assertTrue(so_line_order_new_task_new_project.project_id, "Sales order line should be linked to newly created project")
        self.assertTrue(so_line_order_new_task_new_project.task_id, "Sales order line should be linked to newly created task")
        # service_tracking 'project_only'
        self.assertFalse(so_line_order_only_project.task_id, "Task should not be created")
        self.assertTrue(so_line_order_only_project.project_id, "Sales order line should be linked to newly created project")
