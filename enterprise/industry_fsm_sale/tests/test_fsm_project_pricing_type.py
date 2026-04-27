# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests import tagged

from .common import TestFsmFlowSaleCommon


@tagged('-at_install', 'post_install')
class TestFsmProjectPricingType(TestFsmFlowSaleCommon):

    def test_pricing_type(self):
        """ Test the _compute_pricing_type when the project is a fsm project.

            Test Case:
            =========
            1) Take a project non billable and check if the pricing_type is equal to False
            2) Convert this project as a fsm project, that is set is_fsm to True and check if the pricing type is equal to task_rate.
            3) Add a employee mapping and check if the pricing_type is equal to 'employee_rate'
            4) Set allow_billable to False and check if the pricing_type is equal to False.
        """
        # 1) Take a project non billable and check if the pricing_type is equal to False
        project = self.project_non_billable
        self.assertFalse(project.allow_billable, 'The allow_billable should be false if the project is non billable.')
        self.assertFalse(project.pricing_type, 'The pricing type of this project should be equal to False since it is non billable.')

        # 2) Convert this project as a fsm project, that is set is_fsm to True and check if the pricing type is equal to task_rate.
        project.write({
            'is_fsm': True,
        })

        self.assertTrue(project.is_fsm, 'The project should be a fsm project.')
        self.assertTrue(project.allow_billable, 'By default, a fsm project should be billable.')
        self.assertEqual(project.pricing_type, 'task_rate', 'The pricing type of a fsm project should be equal to task_rate.')
        self.assertTrue(project.filtered_domain(project._search_pricing_type('=', 'task_rate')))
        self.assertFalse(project.filtered_domain(project._search_pricing_type('!=', 'task_rate')))
        self.assertTrue(project.filtered_domain(project._search_pricing_type('!=', 'fixed_rate')))
        self.assertTrue(project.filtered_domain(project._search_pricing_type('!=', 'employee_rate')))
        self.assertTrue(project.filtered_domain(project._search_pricing_type('!=', False)))
        self.assertFalse(project.filtered_domain(project._search_pricing_type('=', 'fixed_rate')))
        self.assertFalse(project.filtered_domain(project._search_pricing_type('=', 'employee_rate')))
        self.assertFalse(project.filtered_domain(project._search_pricing_type('=', False)))

        # 3) Add a employee mapping and check if the pricing_type is equal to 'employee_rate'
        project.write({
            'sale_line_employee_ids': [
                Command.create({
                    'employee_id': self.employee_user.id,
                    'timesheet_product_id': self.service_product_ordered.id,
                }),
            ]
        })
        self.assertEqual(project.pricing_type, 'employee_rate', 'The pricing type of fsm project should be equal to employee_rate when an employee mapping exists in this project.')
        self.assertTrue(project.filtered_domain(project._search_pricing_type('=', 'employee_rate')))
        self.assertTrue(project.filtered_domain(project._search_pricing_type('!=', 'task_rate')))
        self.assertTrue(project.filtered_domain(project._search_pricing_type('!=', 'fixed_rate')))
        self.assertFalse(project.filtered_domain(project._search_pricing_type('!=', 'employee_rate')))
        self.assertTrue(project.filtered_domain(project._search_pricing_type('!=', False)))
        self.assertFalse(project.filtered_domain(project._search_pricing_type('=', 'task_rate')))
        self.assertFalse(project.filtered_domain(project._search_pricing_type('=', 'fixed_rate')))
        self.assertFalse(project.filtered_domain(project._search_pricing_type('=', False)))

        # 4) Set allow_billable to False and check if the pricing_type is equal to False.
        project.write({
            'allow_billable': False,
        })

        self.assertFalse(project.allow_billable, 'The fsm project should be non billable.')
        self.assertFalse(project.pricing_type, 'The pricing type should be equal to False since the project is non billable.')
        self.assertTrue(project.filtered_domain(project._search_pricing_type('=', False)))
        self.assertTrue(project.filtered_domain(project._search_pricing_type('!=', 'task_rate')))
        self.assertTrue(project.filtered_domain(project._search_pricing_type('!=', 'fixed_rate')))
        self.assertTrue(project.filtered_domain(project._search_pricing_type('!=', 'employee_rate')))
        self.assertFalse(project.filtered_domain(project._search_pricing_type('!=', False)))
        self.assertFalse(project.filtered_domain(project._search_pricing_type('=', 'task_rate')))
        self.assertFalse(project.filtered_domain(project._search_pricing_type('=', 'fixed_rate')))
        self.assertFalse(project.filtered_domain(project._search_pricing_type('=', 'employee_rate')))
