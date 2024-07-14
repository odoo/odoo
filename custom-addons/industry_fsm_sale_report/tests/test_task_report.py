# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details

from odoo.exceptions import UserError
from odoo.addons.industry_fsm_sale.tests.common import TestFsmFlowSaleCommon
from odoo.tests import tagged

@tagged('post_install', '-at_install')
class TestTaskReport(TestFsmFlowSaleCommon):

    def test_generate_task_report(self):
        self.assertFalse(self.task.material_line_product_count, "No product should be linked to a new task")

        with self.assertRaises(UserError, msg='Should not be able to get to material without customer set'):
            self.task.action_fsm_view_material()
        self.task.write({'partner_id': self.partner_1.id})
        self.assertFalse(self.task.task_to_invoice, "Nothing should be invoiceable on task")

        expected_product_count = 1
        self.service_product_delivered.with_user(self.project_user).with_context({'fsm_task_id': self.task.id}).fsm_add_quantity()
        self.assertEqual(self.task.material_line_product_count, expected_product_count, f"{expected_product_count} product should be linked to the task")

        expected_product_count += 1
        self.service_product_ordered.with_user(self.project_user).with_context({'fsm_task_id': self.task.id}).fsm_add_quantity()
        self.assertEqual(self.task.material_line_product_count, expected_product_count, f"{expected_product_count} product should be linked to the task")

        expected_product_count += 1
        self.consu_product_delivered.with_user(self.project_user).with_context({'fsm_task_id': self.task.id}).fsm_add_quantity()
        self.assertEqual(self.task.material_line_product_count, expected_product_count, f"{expected_product_count} product should be linked to the task")

        expected_product_count += 1
        self.consu_product_ordered.with_user(self.project_user).with_context({'fsm_task_id': self.task.id}).fsm_add_quantity()
        self.assertEqual(self.task.material_line_product_count, expected_product_count, f"{expected_product_count} product should be linked to the task")

        total_price = self.task.material_line_total_price
        product_without_list_price = self.env['product.product'].create({
            'name': 'Product 0 list price',
            'list_price': 0,
            'type': 'service',
            'invoice_policy': 'delivery',
        })
        expected_product_count += 1
        product_without_list_price.with_user(self.project_user).with_context({'fsm_task_id': self.task.id}).fsm_add_quantity()
        self.assertEqual(self.task.material_line_product_count, expected_product_count, f"{expected_product_count} product should be linked to the task")
        self.assertEqual(total_price, self.task.material_line_total_price, "Total price should not change")

        html_content = self.env['ir.actions.report']._render_qweb_pdf(
            'industry_fsm_report.worksheet_custom', [self.task.id])[0].decode('utf-8').split('\n')

        product_lines_to_find_in_file = {
            "<td><span>Acoustic Bloc Screens</span></td>",
            "<td><span>Individual Workplace</span></td>",
            "<td><span>Consommable product delivery</span></td>",
            "<td><span>Consommable product ordered</span></td>",
        }

        expected_product_lines_to_find_in_file = len(product_lines_to_find_in_file)
        real_product_lines_to_find_in_file = 0

        product_should_not_find_in_file = "<td><span>Product 0 list price</span></td>"

        for product in product_lines_to_find_in_file:
            product_found = False
            for line in html_content:
                self.assertNotIn(product_should_not_find_in_file, line, 'product_without_list_price should not be in the file because its list price is 0')

                if product in line:
                    product_found = True
                    real_product_lines_to_find_in_file += 1
                    break

            self.assertTrue(product_found, f'{product} should be in the file')

        self.assertEqual(expected_product_lines_to_find_in_file, real_product_lines_to_find_in_file)
