# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.sale.tests.common import TestSaleCommon
from odoo.exceptions import ValidationError
from odoo.tests.common import tagged
from psycopg2.errors import NotNullViolation


@tagged('post_install', '-at_install')
class TestSoLineMilestones(TestSaleCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.env['res.config.settings'].create({'group_project_milestone': True}).execute()
        uom_hour = cls.env.ref('uom.product_uom_hour')

        cls.product_delivery_milestones1 = cls.env['product.product'].create({
            'name': "Milestones 1, create project only",
            'standard_price': 15,
            'list_price': 30,
            'type': 'service',
            'invoice_policy': 'delivery',
            'uom_id': uom_hour.id,
            'default_code': 'MILE-DELI4',
            'service_type': 'milestones',
            'service_tracking': 'project_only',
        })
        cls.product_delivery_milestones2 = cls.env['product.product'].create({
            'name': "Milestones 2, create project only",
            'standard_price':20,
            'list_price': 35,
            'type': 'service',
            'invoice_policy': 'delivery',
            'uom_id': uom_hour.id,
            'default_code': 'MILE-DELI4',
            'service_type': 'milestones',
            'service_tracking': 'project_only',
        })
        cls.product_delivery_milestones3 = cls.env['product.product'].create({
            'name': "Milestones 3, create project & task",
            'standard_price': 20,
            'list_price': 35,
            'type': 'service',
            'invoice_policy': 'delivery',
            'uom_id': uom_hour.id,
            'default_code': 'MILE-DELI4',
            'service_type': 'milestones',
            'service_tracking': 'task_in_project',
        })

        cls.sale_order = cls.env['sale.order'].create({
            'partner_id': cls.partner_a.id,
            'partner_invoice_id': cls.partner_a.id,
            'partner_shipping_id': cls.partner_a.id,
        })
        cls.sol1 = cls.env['sale.order.line'].create({
            'product_id': cls.product_delivery_milestones1.id,
            'product_uom_qty': 20,
            'order_id': cls.sale_order.id,
        })
        cls.sol2 = cls.env['sale.order.line'].create({
            'product_id': cls.product_delivery_milestones2.id,
            'product_uom_qty': 30,
            'order_id': cls.sale_order.id,
        })
        cls.sale_order.action_confirm()

        cls.project = cls.sol1.project_id

        cls.milestone1 = cls.env['project.milestone'].create({
            'name': 'Milestone 1',
            'project_id': cls.project.id,
            'is_reached': False,
            'sale_line_id': cls.sol1.id,
            'quantity_percentage': 0.5,
        })

    def test_reached_milestones_delivered_quantity(self):
        self.milestone2 = self.env['project.milestone'].create({
            'name': 'Milestone 2',
            'project_id': self.project.id,
            'is_reached': False,
            'sale_line_id': self.sol2.id,
            'quantity_percentage': 0.2,
        })
        self.milestone3 = self.env['project.milestone'].create({
            'name': 'Milestone 3',
            'project_id': self.project.id,
            'is_reached': False,
            'sale_line_id': self.sol2.id,
            'quantity_percentage': 0.4,
        })

        self.assertEqual(self.sol1.qty_delivered, 0.0, "Delivered quantity should start at 0")
        self.assertEqual(self.sol2.qty_delivered, 0.0, "Delivered quantity should start at 0")

        self.milestone1.is_reached = True
        self.assertEqual(self.sol1.qty_delivered, 10.0, "Delivered quantity should update after a milestone is reached")

        self.milestone2.is_reached = True
        self.assertEqual(self.sol2.qty_delivered, 6.0, "Delivered quantity should update after a milestone is reached")

        self.milestone3.is_reached = True
        self.assertEqual(self.sol2.qty_delivered, 18.0, "Delivered quantity should update after a milestone is reached")

    def test_update_reached_milestone_quantity(self):
        self.milestone1.is_reached = True
        self.assertEqual(self.sol1.qty_delivered, 10.0, "Delivered quantity should start at 10")

        self.milestone1.quantity_percentage = 0.75
        self.assertEqual(self.sol1.qty_delivered, 15.0, "Delivered quantity should update after a milestone's quantity is updated")

    def test_remove_reached_milestone(self):
        self.milestone1.is_reached = True
        self.assertEqual(self.sol1.qty_delivered, 10.0, "Delivered quantity should start at 10")

        self.milestone1.unlink()
        self.assertEqual(self.sol1.qty_delivered, 0.0, "Delivered quantity should update when a milestone is removed")

    def test_compute_sale_line_in_task(self):
        task = self.env['project.task'].create({
            'name': 'Test Task',
            'project_id': self.project.id,
        })
        self.assertEqual(task.sale_line_id, self.sol1, 'The task should have the one of the project linked')
        self.project.sale_line_id = False
        task.sale_line_id = False
        self.assertFalse(task.sale_line_id)
        task.write({'milestone_id': self.milestone1.id})
        self.assertEqual(task.sale_line_id, self.milestone1.sale_line_id, 'The task should have the SOL from the milestone.')
        self.project.sale_line_id = self.sol2
        self.assertEqual(task.sale_line_id, self.sol1, 'The task should keep the SOL linked to the milestone.')

    def test_default_values_milestone(self):
        """ This test checks that newly created milestones have the correct default values:
            1) the first SOL of the SO linked to the project should be used as the default one.
            2) the quantity percentage should be 100% (1.0 in backend).
        """
        project = self.env['project.project'].create({
            'name': 'Test project',
            'sale_line_id': self.sol2.id, # sol1 was created first so we use sol2 to demonstrate that sol1 is used
        })
        milestone = self.env['project.milestone'].with_context({'default_project_id': project.id}).create({
            'name': 'Test milestone',
            'project_id': project.id,
            'is_reached': False,
        })
        # since SOL1 was created before SOL2, it should be selected
        self.assertEqual(milestone.sale_line_id, self.sol1, "The milestone's sale order line should be the first one in the project's SO") #1
        self.assertEqual(milestone.quantity_percentage, 1.0, "The milestone's quantity percentage should be 1.0") #2

    def test_compute_qty_milestone(self):
        """ This test will check that the compute methods for the milestone quantity fields work properly. """
        ratio = self.milestone1.quantity_percentage / self.milestone1.product_uom_qty
        self.milestone1.quantity_percentage = 1.0
        self.assertEqual(self.milestone1.quantity_percentage / self.milestone1.product_uom_qty, ratio, "The ratio should be the same as before")
        self.milestone1.product_uom_qty = 25
        self.assertEqual(self.milestone1.quantity_percentage / self.milestone1.product_uom_qty, ratio, "The ratio should be the same as before")

    def test_create_milestone_on_project_set_on_sales_order(self):
        """
        Regression Test:
        If we confirm an SO with a service with a delivery based on milestones,
        that creates both a project & task, and we set a project on the SO,
        the project for the milestone should be the one set on the SO,
        and no ValidationError or NotNullViolation should be raised.
        """
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'partner_invoice_id': self.partner_a.id,
            'partner_shipping_id': self.partner_a.id,
        })
        self.env['sale.order.line'].create({
            'product_id': self.product_delivery_milestones3.id,
            'product_uom_qty': 20,
            'order_id': sale_order.id,
        })
        try:
            sale_order.action_confirm()
        except (ValidationError, NotNullViolation):
            self.fail("The sale order should be confirmed, "
                      "and no ValidationError or NotNullViolation should be raised, "
                      "for a missing project on the milestone.")

    def test_so_with_milestone_products(self):
        """
        If a SO contains products invoiced based on milestones, a milestone should be created for each of them
        in their project.
        """
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
        })
        products = self.product_delivery_milestones1 | self.product_delivery_milestones2 | self.product_delivery_milestones3
        products.service_tracking = 'task_in_project'

        self.env['sale.order.line'].create([{
            'product_id': product.id,
            'product_uom_qty': 20,
            'order_id': sale_order.id,
        } for product in products])
        sale_order.action_confirm()
        project = sale_order.project_ids
        self.assertEqual(len(project.milestone_ids), 3, "The project should have a milestone for each product.")
        self.assertCountEqual({m.name for m in project.milestone_ids}, {f"[{products[0].default_code}] {p.name}" for p in products}, "The milestones should be named after the products.")

    def test_project_template_with_milestones(self):
        """
        If a milestone product has a project template with configured milestones, use those instead of creating
        a new milestone and set a quantity equal to the quantity of the SOL divided by the number of milestones.
        """
        project_template = self.env['project.project'].create({
            'name': 'Project Template',
        })
        self.env['project.milestone'].create([{
            'project_id': project_template.id,
            'name': str(i),
        } for i in range(4)])
        self.product_delivery_milestones1.project_template_id = project_template.id

        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
        })
        self.env['sale.order.line'].create({
            'product_id': self.product_delivery_milestones1.id,
            'product_uom_qty': 20,
            'order_id': sale_order.id,
        })
        sale_order.action_confirm()

        project = sale_order.project_ids
        self.assertEqual(len(project.milestone_ids), 4, "The generated project should have 4 milestones.")
        self.assertEqual({m.quantity_percentage for m in project.milestone_ids}, {0.25}, "All milestones of the generated project should have a quantity percentage of 25%.")

    def test_project_template_with_milestones_multiple_products(self):
        """
        If multiple products use the same project template, which has configured milestones, use the first product
        on those milestones, but generate the other default milestones as normal
        """
        project_template = self.env['project.project'].create({
            'name': 'Project Template',
        })
        self.env['project.milestone'].create([{
            'project_id': project_template.id,
            'name': str(i),
        } for i in range(4)])
        products = self.product_delivery_milestones1 | self.product_delivery_milestones2
        products.write({
            'project_template_id': project_template.id,
            'service_tracking': 'task_in_project',
        })
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
        })
        self.env['sale.order.line'].create([{
            'product_id': product.id,
            'product_uom_qty': 20,
            'order_id': sale_order.id,
        } for product in products])
        sale_order.action_confirm()

        project = sale_order.project_ids
        self.assertEqual(len(project.milestone_ids), 5, "The project should have 5 milestones")
