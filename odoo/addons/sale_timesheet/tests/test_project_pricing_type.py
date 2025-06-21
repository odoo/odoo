# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from .common import TestCommonSaleTimesheet


@tagged('-at_install', 'post_install')
class TestProjectPricingType(TestCommonSaleTimesheet):

    def test_pricing_type(self):
        """ Test the _compute_pricing_type when the user add a sales order item or some employee mappings in the project

            Test Case:
            =========
            1) Take a project non billable and check if the pricing_type is equal to False
            2) Set allow_billable to True and check if the pricing_type is equal to task_rate (if no SOL and no mappings)
            3) Set a customer and a SOL in the project and check if the pricing_type is equal to fixed_rate (project rate)
            4) Set a employee mapping and check if the pricing_type is equal to employee_rate
        """
        # 1) Take a project non billable and check if the pricing_type is equal to False
        project = self.project_non_billable
        self.assertFalse(project.allow_billable, 'The allow_billable should be false if the project is non billable.')
        self.assertFalse(project.pricing_type, 'The pricing type of this project should be equal to False since it is non billable.')
        self.assertFalse(project.filtered_domain(project._search_pricing_type('=', 'task_rate')))
        self.assertFalse(project.filtered_domain(project._search_pricing_type('=', 'fixed_rate')))
        self.assertFalse(project.filtered_domain(project._search_pricing_type('=', 'employee_rate')))
        self.assertTrue(project.filtered_domain(project._search_pricing_type('=', False)))
        self.assertTrue(project.filtered_domain(project._search_pricing_type('!=', 'task_rate')))
        self.assertTrue(project.filtered_domain(project._search_pricing_type('!=', 'fixed_rate')))
        self.assertTrue(project.filtered_domain(project._search_pricing_type('!=', 'employee_rate')))
        self.assertFalse(project.filtered_domain(project._search_pricing_type('!=', False)))

        # 2) Set allow_billable to True and check if the pricing_type is equal to task_rate (if no SOL and no mappings)
        project.write({
            'allow_billable': True,
        })

        self.assertTrue(project.allow_billable, 'The allow_billable should be updated and equal to True.')
        self.assertFalse(project.sale_order_id, 'The sales order should be unset.')
        self.assertFalse(project.sale_line_id, 'The sales order item should be unset.')
        self.assertFalse(project.sale_line_employee_ids, 'The employee mappings should be empty.')
        self.assertEqual(project.pricing_type, 'task_rate', 'The pricing type should be equal to task_rate.')
        self.assertTrue(project.filtered_domain(project._search_pricing_type('=', 'task_rate')))
        self.assertFalse(project.filtered_domain(project._search_pricing_type('=', 'fixed_rate')))
        self.assertFalse(project.filtered_domain(project._search_pricing_type('=', 'employee_rate')))
        self.assertFalse(project.filtered_domain(project._search_pricing_type('=', False)))
        self.assertFalse(project.filtered_domain(project._search_pricing_type('!=', 'task_rate')))
        self.assertTrue(project.filtered_domain(project._search_pricing_type('!=', 'fixed_rate')))
        self.assertTrue(project.filtered_domain(project._search_pricing_type('!=', 'employee_rate')))
        self.assertTrue(project.filtered_domain(project._search_pricing_type('!=', False)))

        # 3) Set a customer and a SOL in the project and check if the pricing_type is equal to fixed_rate (project rate)
        project.write({
            'partner_id': self.partner_b.id,
            'sale_line_id': self.so.order_line[0].id,
        })

        self.assertEqual(project.sale_order_id, self.so, 'The sales order should be equal to the one set in the project.')
        self.assertEqual(project.sale_line_id, self.so.order_line[0], 'The sales order item should be the one chosen.')
        self.assertEqual(project.pricing_type, 'fixed_rate', 'The pricing type should be equal to fixed_rate since the project has a sales order item.')
        self.assertFalse(project.filtered_domain(project._search_pricing_type('=', 'task_rate')))
        self.assertTrue(project.filtered_domain(project._search_pricing_type('=', 'fixed_rate')))
        self.assertFalse(project.filtered_domain(project._search_pricing_type('=', 'employee_rate')))
        self.assertFalse(project.filtered_domain(project._search_pricing_type('=', False)))
        self.assertTrue(project.filtered_domain(project._search_pricing_type('!=', 'task_rate')))
        self.assertFalse(project.filtered_domain(project._search_pricing_type('!=', 'fixed_rate')))
        self.assertTrue(project.filtered_domain(project._search_pricing_type('!=', 'employee_rate')))
        self.assertTrue(project.filtered_domain(project._search_pricing_type('!=', False)))

        # 4) Set a employee mapping and check if the pricing_type is equal to employee_rate
        project.write({
            'sale_line_employee_ids': [(0, 0, {
                'employee_id': self.employee_user.id,
                'sale_line_id': self.so.order_line[1].id,
            })]
        })

        self.assertEqual(len(project.sale_line_employee_ids), 1, 'The project should have an employee mapping.')
        self.assertEqual(project.pricing_type, 'employee_rate', 'The pricing type should be equal to employee_rate since the project has an employee mapping.')
        self.assertFalse(project.filtered_domain(project._search_pricing_type('=', 'task_rate')))
        self.assertFalse(project.filtered_domain(project._search_pricing_type('=', 'fixed_rate')))
        self.assertTrue(project.filtered_domain(project._search_pricing_type('=', 'employee_rate')))
        self.assertFalse(project.filtered_domain(project._search_pricing_type('=', False)))
        self.assertTrue(project.filtered_domain(project._search_pricing_type('!=', 'task_rate')))
        self.assertTrue(project.filtered_domain(project._search_pricing_type('!=', 'fixed_rate')))
        self.assertFalse(project.filtered_domain(project._search_pricing_type('!=', 'employee_rate')))
        self.assertTrue(project.filtered_domain(project._search_pricing_type('!=', False)))

        # Even if the project has no sales order item, since it has an employee mapping, the pricing type must be equal to employee_rate.
        project.write({
            'sale_line_id': False,
        })
        self.assertFalse(project.sale_order_id, 'The sales order of the project should be empty.')
        self.assertFalse(project.sale_line_id, 'The sales order item of the project should be empty.')
        self.assertEqual(project.pricing_type, 'employee_rate', 'The pricing type should always be equal to employee_rate.')
        self.assertFalse(project.filtered_domain(project._search_pricing_type('=', 'task_rate')))
        self.assertFalse(project.filtered_domain(project._search_pricing_type('=', 'fixed_rate')))
        self.assertTrue(project.filtered_domain(project._search_pricing_type('=', 'employee_rate')))
        self.assertFalse(project.filtered_domain(project._search_pricing_type('=', False)))
        self.assertTrue(project.filtered_domain(project._search_pricing_type('!=', 'task_rate')))
        self.assertTrue(project.filtered_domain(project._search_pricing_type('!=', 'fixed_rate')))
        self.assertFalse(project.filtered_domain(project._search_pricing_type('!=', 'employee_rate')))
        self.assertTrue(project.filtered_domain(project._search_pricing_type('!=', False)))
