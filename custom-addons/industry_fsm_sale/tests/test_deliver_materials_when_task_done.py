# Part of Odoo. See LICENSE file for full copyright and licensing details

from .common import TestFsmFlowSaleCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestDeliverMaterialsWhenTaskDone(TestFsmFlowSaleCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.consu_product = cls.env['product.product'].create({
            'name': 'Consommable product',
            'list_price': 40,
            'type': 'consu',
            'invoice_policy': 'delivery',
        })

        cls.service_product = cls.env['product.product'].create({
            'name': "Service Ordered, create task in fsm",
            'standard_price': 30,
            'list_price': 90,
            'type': 'service',
            'invoice_policy': 'delivery',
            'service_type': 'milestones',
            'service_tracking': 'task_global_project',
            'project_id': cls.fsm_project.id,
        })

    def test_deliver_materials_when_task_done(self):
        """ Test system automatically updates materials when task is done.

            Test Case:
            =========
            1) Add some materials, only the qty_delivered is empty (equal to 0)
            2) Mark the task as done
            3) Check if qty_delivered for each SOL contain material of the task is updated and equal to the product_uom_qty.
        """
        self.assertFalse(self.task.material_line_product_count, "No product should be linked to a new task.")
        self.task.write({'partner_id': self.partner_1.id})
        self.task.with_user(self.project_user).action_fsm_view_material()
        self.consu_product.with_user(self.project_user).with_context({'fsm_task_id': self.task.id}).set_fsm_quantity(5)
        self.assertEqual(self.task.material_line_product_count, 5, "5 products should be linked to the task")

        product_sol = self.task.sale_order_id.order_line.filtered(lambda sol: sol.product_id == self.consu_product)
        self.assertEqual(product_sol.product_uom_qty, 5, "The quantity of this product should be equal to 5.")

        self.task.action_fsm_validate()
        self.assertTrue(self.task.fsm_done, 'The task should be mark as done')
        self.assertEqual(product_sol.qty_delivered, product_sol.product_uom_qty, 'The delivered quantity for the ordered product should be updated when the task is marked as done.')

    def test_milestone_service_product_delivery_when_task_done(self):
        """ Test system doesn't automatically updates delivered quantities
            for milestone service products when task is done.
            Instead, it's computed based on reached milestones.

            Test Case:
            =========
            1) Add service product with invoice policy 'milestone'
            2) Mark the task as done
            3) Check if qty_delivered for SOL is still 0. (no milestone is created yet)
            4) Create a milestone with quantity 50%
            5) Check if qty_delivered for SOL is updated to 0.5.
        """
        SaleOrder = self.env['sale.order'].with_context(tracking_disable=True)
        SaleOrderLine = self.env['sale.order.line'].with_context(tracking_disable=True)

        sale_order = SaleOrder.create({
            'partner_id': self.partner_1.id,
            'partner_invoice_id': self.partner_1.id,
            'partner_shipping_id': self.partner_1.id,
        })

        sale_order_line = SaleOrderLine.create({
            'product_id': self.service_product.id,
            'product_uom_qty': 4,
            'order_id': sale_order.id,
        })

        sale_order.action_confirm()
        task = self.env['project.task'].search([('sale_order_id', '=', sale_order.id)], limit=1)

        task.action_fsm_validate()
        self.assertTrue(task.fsm_done, 'The task should be mark as done')
        self.assertEqual(sale_order_line.qty_delivered, 0, 'The delivered quantity should remain 0 as no milestone is created yet.')

        milestone = self.env['project.milestone'].create({
            'name': 'Test Milestone',
            'sale_line_id': sale_order_line.id,
            'quantity_percentage': 0.5,
            'is_reached': False,
            'project_id': task.project_id.id,
        })
        self.assertEqual(sale_order_line.qty_delivered, 0, 'The delivered quantity should remain 0 as the milestone is not reached yet.')

        milestone.is_reached = True
        self.assertEqual(sale_order_line.qty_delivered, 2, 'The delivered quantity should be updated to 2 as the milestone with 50% of quantity percentage is reached.')
