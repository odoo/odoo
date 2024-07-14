# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details

from odoo import Command
from odoo.tests import tagged

from .common import TestFsmFlowSaleCommon


@tagged('-at_install', 'post_install')
class TestIndustryFsmEmployeeRate(TestFsmFlowSaleCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Add task model with context in variable to facilitate the task creation in this project
        cls.Task = cls.env['project.task'].with_context({
            'mail_create_nolog': True,
            'default_project_id': cls.fsm_project_employee_rate.id,
            'default_user_ids': cls.project_user,
        })

    def test_fsm_employee_rate(self):
        """ Test the employee rate as pricing type in fsm project

            Test Case:
            =========
            1) Create task with timesheets containing some employees in employee mappings.
            2) Validate the task and check if the SOL in each timesheet is correct with the correct product.
            3) Create task with a timesheet containing no employee in employee mappings.
            4) Validate the task and check if the SOL in each timesheet is the one in the task with the default product defined in the project.
            5) Create task with timesheets with only the employees defined in the mapping.
            6) Validate the task and check if the SOL in the task contains the product in the first mapping found based on the timesheets.
        """
        self.assertTrue(self.fsm_project_employee_rate.is_fsm, 'The project should be a fsm project.')
        self.assertEqual(self.fsm_project_employee_rate.pricing_type, 'employee_rate', 'The pricing of this fsm project should be employee rate since there are some employee mappings into it.')
        self.assertEqual(len(self.fsm_project_employee_rate.sale_line_employee_ids), 3, 'The number of employee mappings in this fsm project should be equal to 3 mappings.')

        # 1) Create task with timesheets containing some employees in employee mappings.
        task = self.Task.create({
            'name': 'Fsm Task',
            'timesheet_ids': [
                Command.create({
                    'name': '/',
                    'employee_id': self.employee_user.id,
                    'unit_amount': 1.0,
                    'project_id': self.fsm_project_employee_rate.id,
                }),
                Command.create({
                    'name': '/',
                    'employee_id': self.employee_user2.id,
                    'unit_amount': 1.0,
                    'project_id': self.fsm_project_employee_rate.id,
                }),
                Command.create({
                    'name': '/',
                    'employee_id': self.employee_manager.id,
                    'unit_amount': 1.0,
                    'project_id': self.fsm_project_employee_rate.id,
                }),
            ]
        })
        self.assertEqual(len(task.timesheet_ids), 3, 'The task should have 3 timesheets.')
        self.assertFalse(task.sale_line_id, 'The task should have no SOL.')

        self.consu_product_ordered.with_user(self.project_user).with_context({'fsm_task_id': task.id}).set_fsm_quantity(1.0)
        task.sale_order_id.write({
            'order_line': [
                Command.create({
                    'product_id': self.service_timesheet.id,
                    'product_uom_qty': 2.0,
                    'name': '/',
                }),
            ]
        })
        if task.sale_order_id.state != 'sale':
            task.sale_order_id.action_confirm()
        self.assertEqual(len(task.sale_order_id.order_line), 2)
        service_timesheet_order_line = task.sale_order_id.order_line.filtered(lambda order_line: order_line.product_id == self.service_timesheet)

        task.write({
            'timesheet_ids': [
                Command.create({
                    'name': '/',
                    'employee_id': self.employee_manager.id,
                    'unit_amount': 1.0,
                    'so_line': service_timesheet_order_line.id,
                    'is_so_line_edited': True,
                    'project_id': self.fsm_project_employee_rate.id,
                }),
            ]
        })
        self.assertEqual(len(task.timesheet_ids), 4)

        # 2) Validate the task and check if the SOL in each timesheet is correct with the correct product.
        task.action_fsm_validate()
        self.assertEqual(len(task.timesheet_ids.so_line), 4, 'Each timesheet should have a different SOL.')
        self.assertEqual(task.sale_order_id.order_line.mapped('qty_delivered'), [1.0] * 5, 'The generated SO should have 4 SOLs in which the quantity delivered should be equal to 1 hour.')
        self.assertEqual(task.sale_line_id.product_id, self.fsm_project_employee_rate.timesheet_product_id, 'The SOL linked to the task should have the default service product of the product.')

        # 3) Create task with a timesheet containing no employee in employee mappings.
        task = self.Task.create({
            'name': 'Fsm Task',
            'timesheet_ids': [
                Command.create({
                    'name': '/',
                    'employee_id': self.employee_manager.id,
                    'unit_amount': 2.0,
                    'project_id': self.fsm_project_employee_rate.id,
                })
            ]
        })
        self.assertEqual(len(task.timesheet_ids), 1, 'The task should have 1 timesheet.')
        self.assertFalse(task.sale_line_id, 'The task should have no SOL.')

        # 4) Validate the task and check if the SOL in each timesheet is the one in the task with the default product defined in the project.
        task.action_fsm_validate()
        self.assertEqual(task.sale_line_id, task.timesheet_ids.so_line, 'The SOL in task and timesheet should be the same.')
        self.assertEqual(task.sale_line_id.product_id, self.fsm_project_employee_rate.timesheet_product_id, 'The product in the SOL should be the default service product defined in the project.')

        # 5) Create task with timesheets with only the employees defined in the mapping.
        task = self.Task.create({
            'name': 'Fsm Task',
            'timesheet_ids': [
                Command.create({
                    'name': '/',
                    'employee_id': self.employee_user3.id,
                    'unit_amount': 2.0,
                    'project_id': self.fsm_project_employee_rate.id,
                }),
                Command.create({
                    'name': '/',
                    'employee_id': self.employee_user2.id,
                    'unit_amount': 2.0,
                    'project_id': self.fsm_project_employee_rate.id,
                }),
            ]
        })
        self.assertEqual(len(task.timesheet_ids), 2, 'The task should have 2 timesheets.')
        self.assertFalse(task.sale_line_id, 'The task should have no SOL.')

        # 6) Validate the task and check if the SOL in the task contains the product in the first mapping found based on the timesheets.
        task.action_fsm_validate()

        # Search the first mapping based on the timesheets in the task
        first_employee_mapping = \
            self.fsm_project_employee_rate.sale_line_employee_ids\
                                     .filtered(
                                         lambda mapping:
                                             mapping.employee_id in task.timesheet_ids.employee_id
                                     )[:1]
        self.assertEqual(task.sale_line_id.product_id, first_employee_mapping.timesheet_product_id, 'The product choose for the SOL in the task should be the product in the first mapping found based on the timesheets in the task.')
        self.assertEqual(first_employee_mapping.employee_id, self.employee_user2, 'The mapping found should be the one for the Employee User 2.')
        self.assertEqual(first_employee_mapping.timesheet_product_id, self.product_delivery_timesheet1, 'The product in this mapping should be the one defined the Employee User 2.')
        self.assertEqual(task.sale_order_id.order_line.mapped('qty_delivered'), [2.0] * 2, 'Each SOL generated should have 2 hours as quantity delivered.')

    def test_fsm_employee_rate_with_same_product_in_two_mappings(self):
        """ Test when a same service product is in 2 employee mappings for fsm project.

            Test Case:
            =========
            1) Update the employee mappings in the fsm project to have 2 mappings for the same service product.
            2) Create task with timesheets containing the mappings with the same product
            3) Validate the task and check if the SO generated contains 2 SOLs for the same product but with a different price unit.
        """
        self.fsm_project_employee_rate.sale_line_employee_ids.unlink()
        ProjectSaleLineEmployeeMap = self.env['project.sale.line.employee.map'].with_context(default_project_id=self.fsm_project_employee_rate.id)
        employee_manager_mapping = ProjectSaleLineEmployeeMap.create({
            'employee_id': self.employee_manager.id,
            'timesheet_product_id': self.product_order_timesheet1.id,
        })
        employee_user2_mapping = ProjectSaleLineEmployeeMap.create({
            'employee_id': self.employee_user2.id,
            'timesheet_product_id': self.product_order_timesheet1.id,
        })
        ProjectSaleLineEmployeeMap.create({
            'employee_id': self.employee_user3.id,
            'timesheet_product_id': self.product_delivery_timesheet2.id,
        })
        self.fsm_project_employee_rate.sale_line_employee_ids._compute_price_unit()
        employee_manager_mapping.write({'price_unit': 20.0})
        self.assertEqual(len(self.fsm_project_employee_rate.sale_line_employee_ids), 3)
        self.assertEqual(employee_manager_mapping.timesheet_product_id, employee_user2_mapping.timesheet_product_id, 'Both mappings should have the same service product.')
        self.assertNotEqual(employee_manager_mapping.price_unit, employee_user2_mapping.price_unit, 'The price unit of both mappings with the same service product should be different.')

        # 2) Create task with timesheets containing the mappings with the same product
        task = self.Task.create({
            'name': 'Fsm Task',
            'timesheet_ids': [
                Command.create({
                    'name': '/',
                    'employee_id': self.employee_manager.id,
                    'unit_amount': 1.0,
                    'project_id': self.fsm_project_employee_rate.id,
                }),
                Command.create({
                    'name': '/',
                    'employee_id': self.employee_user2.id,
                    'unit_amount': 1.0,
                    'project_id': self.fsm_project_employee_rate.id,
                }),
            ]
        })
        self.assertEqual(len(task.timesheet_ids), 2, 'The task should have 2 timesheets.')

        # 3) Validate the task and check if the SO generated contains 2 SOLs for the same product but with a different price unit.
        task.action_fsm_validate()
        so = task.sale_order_id
        self.assertEqual(len(so.order_line), 2, 'The generated SO should have 2 SOLs.')
        self.assertEqual(so.order_line.product_id, self.product_order_timesheet1, 'The both SOLs of this generated SO should have the same service product.')
        self.assertNotEqual(so.order_line[0].price_unit, so.order_line[1].price_unit, 'The only different in the both SOLs is the price unit.')
