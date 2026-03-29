# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from .common import TestCommonSaleTimesheet
from odoo.tests import tagged, Form


@tagged('post_install', '-at_install')
class TestProject(TestCommonSaleTimesheet):

    def setUp(self):
        super().setUp()
        self.project_global.write({
            'sale_line_id': self.so.order_line[0].id,
        })

    def test_fetch_sale_order_items(self):
        """ Test _fetch_sale_order_items and _get_sale_order_items methods

            This test will check we have the SOLs linked to the project and its tasks.

            Test Case:
            =========
            1) No SOLs and SO should be found on a non billable project
            2) Sol linked to the project should be fetched
            3) SOL linked to the project and its task should be fetched
            4) remove the SOL linked to the project and check the SOL linked to the task is fetched
            5) Add an additional domain in the tasks to check if we can fetch with an additional filter
                for instance, only the SOLs linked to the folded tasks.
            6) Set allàw_billable=False and check no SOL is found since the project is not billable.
        """
        self.assertFalse(self.project_non_billable._fetch_sale_order_items())
        self.assertFalse(self.project_non_billable._get_sale_order_items())
        self.assertFalse(self.project_non_billable._get_sale_orders())

        sale_item = self.so.order_line[0]
        self.project_global.invalidate_cache()
        expected_task_sale_order_items = self.project_global.tasks.sale_line_id
        expected_sale_order_items = sale_item | expected_task_sale_order_items
        self.assertEqual(self.project_global._fetch_sale_order_items(), expected_sale_order_items)
        self.assertEqual(self.project_global._get_sale_order_items(), expected_sale_order_items)
        self.assertEqual(self.project_global._get_sale_orders(), self.so)

        task = self.env['project.task'].create({
            'name': 'Task with SOL',
            'project_id': self.project_global.id,
            'sale_line_id': self.so.order_line[1].id,
        })

        self.assertEqual(task.project_id, self.project_global)
        self.assertEqual(task.sale_line_id, self.so.order_line[1])
        self.assertEqual(task.sale_order_id, self.so)
        sale_lines = self.project_global._get_sale_order_items()
        self.assertEqual(sale_lines, task.sale_line_id + self.project_global.sale_line_id, 'The Sales Order Items found should be the one linked to the project and the one of project task.')
        self.assertEqual(self.project_global._get_sale_orders(), self.so, 'The Sales Order fetched should be the one of the both sale_lines fetched.')

        self.project_global.write({
            'sale_line_id': False,
        })
        self.project_global.invalidate_cache()
        expected_task_sale_order_items |= task.sale_line_id
        self.assertEqual(self.project_global._get_sale_order_items(), expected_task_sale_order_items)
        self.assertEqual(self.project_global._get_sale_orders(), self.so)

        new_stage = self.env['project.task.type'].create({
            'name': 'New',
            'sequence': 1,
            'project_ids': [Command.set(self.project_global.ids)],
        })
        done_stage = self.env['project.task.type'].create({
            'name': 'Done',
            'sequence': 2,
            'project_ids': [Command.set(self.project_global.ids)],
            'fold': True,
            'is_closed': True,
        })
        task.write({
            'stage_id': done_stage.id,
        })
        self.env['project.task.type'].flush()

        self.assertFalse(self.project_global._fetch_sale_order_items({'project.task': [('stage_id.fold', '=', False)]}))
        self.assertEqual(self.project_global._fetch_sale_order_items({'project.task': [('stage_id.fold', '=', True)]}), task.sale_line_id)

        task2 = self.env['project.task'].create({
            'name': 'Task 2',
            'project_id': self.project_global.id,
            'sale_line_id': sale_item.id,
            'stage_id': new_stage.id,
        })

        self.assertEqual(self.project_global._fetch_sale_order_items({'project.task': [('stage_id.fold', '=', False)]}), task2.sale_line_id)
        self.assertEqual(self.project_global._fetch_sale_order_items({'project.task': [('stage_id.fold', '=', True)]}), task.sale_line_id)

        self.project_global.allow_billable = False
        self.assertFalse(self.project_global._get_sale_order_items())
        self.assertFalse(self.project_global._get_sale_orders())

    def test_compute_cost_in_employee_mappings(self):
        self.assertFalse(self.project_global.sale_line_employee_ids)
        employee_mapping = self.env['project.sale.line.employee.map'] \
            .with_context(default_project_id=self.project_global.id) \
            .create({
                'employee_id': self.employee_manager.id,
                'sale_line_id': self.project_global.sale_line_id.id,
            })
        self.assertFalse(employee_mapping.is_cost_changed)
        self.assertEqual(employee_mapping.cost, self.employee_manager.timesheet_cost)

        employee_mapping.cost = 5
        self.assertTrue(employee_mapping.is_cost_changed)
        self.assertEqual(employee_mapping.cost, 5)

        self.employee_manager.timesheet_cost = 80
        self.assertTrue(employee_mapping.is_cost_changed)
        self.assertEqual(employee_mapping.cost, 5)

        employee_mapping.employee_id = self.employee_user
        self.assertTrue(employee_mapping.is_cost_changed)
        self.assertEqual(employee_mapping.cost, 5)

        employee_mapping.cost = self.employee_user.timesheet_cost
        employee_mapping.employee_id = self.employee_company_B
        self.assertEqual(employee_mapping.cost, self.employee_company_B.timesheet_cost)

    def test_open_product_form_with_default_service_policy(self):
        form = Form(self.env['product.product'].with_context(default_detailed_type='service', default_service_policy='delivered_timesheet'))
        self.assertEqual('delivered_timesheet', form.service_policy)
