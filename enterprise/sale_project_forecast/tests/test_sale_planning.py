# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details
from freezegun import freeze_time
from datetime import datetime

from odoo.tests import Form, tagged

from odoo.addons.sale_planning.tests.test_sale_planning import TestCommonSalePlanning

@tagged('post_install', '-at_install')
class TestSaleForecast(TestCommonSalePlanning):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.planning_partner = cls.env['res.partner'].create({
            'name': 'Customer Credee'
        })

        cls.plannable_forecast_product = cls.env['product.product'].create({
            'name': 'Junior Developer Service',
            'type': 'service',
            'planning_enabled': True,
            'planning_role_id': cls.planning_role_junior.id,
            'service_tracking': 'task_in_project',
        })
        cls.plannable_forecast_so = cls.env['sale.order'].create({
            'partner_id': cls.planning_partner.id,
        })
        cls.plannable_forecast_sol = cls.env['sale.order.line'].create({
            'order_id': cls.plannable_forecast_so.id,
            'product_id': cls.plannable_forecast_product.id,
            'product_uom_qty': 10,
        })

        product_task_in_project1 = cls.env['product.product'].create({
            'name': 'Task in Project',
            'type': 'service',
            'service_tracking': 'task_in_project',
        })
        product_task_in_project2 = cls.env['product.product'].create({
            'name': 'Task in Project 2',
            'type': 'service',
            'service_tracking': 'task_in_project',
        })
        sale_order = cls.env['sale.order'].create({
            'partner_id': cls.planning_partner.id,
        })
        cls.sale_order_line1 = cls.env['sale.order.line'].create({
            'order_id': sale_order.id,
            'product_id': product_task_in_project1.id,
        })
        cls.sale_order_line2 = cls.env['sale.order.line'].create({
            'order_id': sale_order.id,
            'product_id': product_task_in_project2.id,
        })
        sale_order.action_confirm()

    @classmethod
    def setUpEmployees(cls):
        super().setUpEmployees()
        user_group_employee = cls.env.ref('base.group_user')
        user_group_project_user = cls.env.ref('project.group_project_user')
        cls.user_projectuser_wout = cls.env['res.users'].with_context({'no_reset_password': True}).create({
            'name': 'Wout',
            'login': 'Wout',
            'email': 'wout@test.com',
            'groups_id': [(6, 0, [user_group_employee.id, user_group_project_user.id])],
        })
        cls.employee_wout.write({'user_id': cls.user_projectuser_wout.id})

    def test_sale_line_id_value_depending_project(self):
        line1_project = self.sale_order_line1.project_id
        line2_project = self.sale_order_line2.project_id

        slot1 = self.env['planning.slot'].create({
            'project_id': line1_project.id,
        })
        self.assertEqual(slot1.sale_line_id, line1_project.sale_line_id, 'Sale order item of Planning should be same as project')

        slot1.write({'project_id': line2_project.id})
        # changing project of slot should not change to new project's sol if sol of slot is already set
        self.assertEqual(slot1.sale_line_id, line1_project.sale_line_id, 'Sale order item of Planning should not change to new project\'s sol if it\'s already set')

    @freeze_time('2023-1-1')
    def test_archive_employee_should_move_shifts_to_open_shifts(self):
        slot = self.env['planning.slot'].create([{
            'resource_id': self.employee_joseph.resource_id.id,
            'start_datetime': datetime(2023, 1, 2, 8, 0),
            'end_datetime': datetime(2023, 1, 2, 17, 0),
            'sale_line_id': self.sale_order_line1.id,
            'project_id': self.sale_order_line1.project_id.id,
        }])
        self.employee_joseph.action_archive()
        self.assertFalse(slot.resource_id, "Resource of the shift should be open")
        self.assertEqual(slot.sale_line_id, self.sale_order_line1, "Project should be the same")
        self.assertEqual(slot.project_id, self.sale_order_line1.project_id, "SOL should be the same")
