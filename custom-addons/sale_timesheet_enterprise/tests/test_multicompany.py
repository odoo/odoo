# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.sale_timesheet.tests.common import TestCommonSaleTimesheet
from odoo.fields import Command
from odoo.tests import tagged


@tagged('-at_install', 'post_install')
class TestSaleTimesheetEnterpriseMultiCompany(TestCommonSaleTimesheet):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        Project = cls.env['project.project'].with_context(tracking_disable=True)
        cls.service_timesheet_product = cls.env.ref('sale_timesheet.time_product')
        cls.project_billable_tasks = Project.create({
            'name': "Billable on project",
            'company_id': cls.env.company.id,
            'allow_billable': True,
            'timesheet_product_id': cls.service_timesheet_product.id,
            'partner_id': cls.partner_a.id,
        })

        Task = cls.env['project.task']
        cls.task = Task.with_context(default_project_id=cls.project_billable_tasks.id).create({
            'name': 'first task',
            'partner_id': cls.partner_a.id,
            'allocated_hours': 10,
        })
        cls.env['account.analytic.line'].create({
            'name': 'Test Timesheet',
            'employee_id': cls.employee_manager.id,
            'project_id': cls.project_billable_tasks.id,
            'task_id': cls.task.id,
        })

    def test_billable_project(self):
        wizard = self.env['project.create.sale.order'].with_context(
            allowed_company_ids=[self.env.company.id, self.company_data_2['company'].id],
            company_id=self.company_data_2['company'].id,
            active_id=self.project_billable_tasks.id,
            active_model='project.project'
        ).create({
            'line_ids': [
                Command.create({'product_id': self.service_timesheet_product.id, 'price_unit': self.service_timesheet_product.lst_price}),
            ],
        })

        action = wizard.action_create_sale_order()
        sale_order = self.env['sale.order'].browse(action['res_id'])

        self.assertEqual(sale_order.company_id.id, self.task.company_id.id, "The company of the sale order should be the same as the one from the task")
