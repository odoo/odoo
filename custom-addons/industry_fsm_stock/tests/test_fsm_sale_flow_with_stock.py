# Part of Odoo. See LICENSE file for full copyright and licensing details

from datetime import datetime
from odoo.addons.industry_fsm_sale.tests.common import TestFsmFlowSaleCommon
from odoo.exceptions import UserError
from odoo.tests import tagged


@tagged('-at_install', 'post_install')
class TestFsmFlowSaleWithStock(TestFsmFlowSaleCommon):
    """
        The sale flow is tested here because when the stock module is installed, its behavior is modified. To ensure the behavior still works without the stock module, a test is run
        at-install on the industry_fsm_sale module
    """

    def test_fsm_flow(self):
        """
        Test Cases:
        ==========
        1) Add task and Assert no products added
        2) Add and remove different quantities of products:
            - Service (order/delivered)
            - Consumable (order/delivered)
            And assert after each operation on product count
        3) Set product quantity after confirming SO
        """
        self.assertFalse(self.task.material_line_product_count, "No product should be linked to a new task")
        with self.assertRaises(UserError, msg='Should not be able to get to material without customer set'):
            self.task.action_fsm_view_material()
        self.task.write({'partner_id': self.partner_1.id})
        self.assertFalse(self.task.task_to_invoice, "Nothing should be invoiceable on task")
        self.task.with_user(self.project_user).action_fsm_view_material()

        expected_product_count = 1
        self.service_product_delivered.with_user(self.project_user).with_context({'fsm_task_id': self.task.id}).fsm_add_quantity()
        self.assertEqual(self.task.material_line_product_count, expected_product_count, f"{expected_product_count} product should be linked to the task")

        expected_product_count += 1
        self.service_product_delivered.with_user(self.project_user).with_context({'fsm_task_id': self.task.id}).fsm_add_quantity()
        self.assertEqual(self.task.material_line_product_count, expected_product_count, f"{expected_product_count} product should be linked to the task")

        expected_product_count += 1
        self.consu_product_delivered.with_user(self.project_user).with_context({'fsm_task_id': self.task.id}).fsm_add_quantity()
        self.assertEqual(self.task.material_line_product_count, expected_product_count, f"{expected_product_count} product should be linked to the task")

        expected_product_count += 1
        self.consu_product_ordered.with_user(self.project_user).with_context({'fsm_task_id': self.task.id}).fsm_add_quantity()
        self.assertEqual(self.task.material_line_product_count, expected_product_count, f"{expected_product_count} product should be linked to the task")

        expected_product_count -= 1
        self.consu_product_ordered.with_user(self.project_user).with_context({'fsm_task_id': self.task.id}).fsm_remove_quantity()
        self.assertEqual(self.task.material_line_product_count, expected_product_count, f"{expected_product_count} product should be linked to the task")

        expected_product_count += 1
        self.service_product_ordered.with_user(self.project_user).with_context({'fsm_task_id': self.task.id}).fsm_add_quantity()
        self.assertEqual(self.task.material_line_product_count, expected_product_count, f"{expected_product_count} product should be linked to the task")

        quantity_to_add = 5
        expected_product_count += quantity_to_add
        self.consu_product_ordered.with_user(self.project_user).with_context({'fsm_task_id': self.task.id}).set_fsm_quantity(quantity_to_add)
        self.assertEqual(self.task.material_line_product_count, expected_product_count, f"{expected_product_count} product should be linked to the task")

        # timesheet
        values = {
            'task_id': self.task.id,
            'project_id': self.task.project_id.id,
            'date': datetime.now(),
            'name': 'test timesheet',
            'user_id': self.env.uid,
            'unit_amount': 0.25,
            'employee_id': self.env['hr.employee'].create({'user_id': self.env.uid}).id,
        }
        self.env['account.analytic.line'].create(values)
        self.assertEqual(self.task.material_line_product_count, expected_product_count, "Timesheet should not appear in material")

        # validation and SO
        self.assertFalse(self.task.fsm_done, "Task should not be validated")
        self.assertEqual(len(self.task.sale_order_id.order_line), 4)

        order_line = self.task.sale_order_id.order_line.filtered(lambda l: l.name == self.service_product_ordered.name)
        self.assertEqual(order_line.product_uom_qty, 1)
        self.task.with_user(self.project_user).action_fsm_validate()
        self.assertTrue(self.task.fsm_done, "Task should be validated")
        self.assertEqual(self.task.sale_order_id.state, 'sale', "Sale order should be confirmed")

        # Add product quantity after confirming the SO
        self.service_product_ordered.with_user(self.project_user).with_context({'fsm_task_id': self.task.id}).set_fsm_quantity(9)
        self.assertEqual(order_line.product_uom_qty, 9)
        expected_product_count += 8
        self.assertEqual(self.task.material_line_product_count, expected_product_count, f"{expected_product_count} product should be linked to the task")

        # invoice
        self.assertTrue(self.task.task_to_invoice, "Task should be invoiceable")
        invoice_ctx = self.task.action_create_invoice()['context']
        invoice_wizard = self.env['sale.advance.payment.inv'].with_context(invoice_ctx).create({})
        invoice_wizard.create_invoices()
        self.assertFalse(self.task.task_to_invoice, "Task should not be invoiceable")

        # quotation
        self.assertEqual(self.task.quotation_count, 0, "0 quotation should be linked to the task since we don't create a quotation via the Create Quotation button.")
        quotation_context = self.task.action_fsm_create_quotation()['context']
        quotation = self.env['sale.order'].with_context(quotation_context).create({})
        self.assertEqual(quotation.task_id, self.task)
        self.task._compute_quotation_count()  # it means we return to the form view of the task, So the compute will be trigger again.
        self.assertEqual(self.task.quotation_count, 1, '1 quotation should be linked to the task since we create a quotation via the Create Quotation button.')
        self.assertEqual(self.task.action_fsm_view_quotations()['res_id'], quotation.id, "Created quotation id should be in the action")
