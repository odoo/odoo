# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details

from odoo import Command
from odoo.addons.industry_fsm_sale.tests.common import TestFsmFlowSaleCommon
from odoo.tests import tagged

@tagged('post_install', '-at_install')
class TestWorksheet(TestFsmFlowSaleCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.worksheet_template = cls.env['worksheet.template'].with_context(worksheet_no_generation=True).create({
            'name': 'New worksheet',
            'color': 4,
            'res_model': 'project.task',
        })
        cls.fsm_project.write({
            'allow_worksheets': True,
            'worksheet_template_id': cls.worksheet_template.id,
        })
        cls.second_worksheet_template = cls.env['worksheet.template'].with_context(worksheet_no_generation=True).create({
            'name': 'Second worksheet',
            'color': 3,
            'res_model': 'project.task',
        })

    def test_service_worksheet_template_propagation(self):
        """
            1) Add new service with worksheet template != its project worksheet template
            2) Add new Sale order with this service
            3) Assert task added with the good worksheet template and project
        """
        task = self.env['project.task'].create({
            'name': 'Fsm task',
            'project_id': self.fsm_project.id,
            'partner_id': self.partner_1.id,
        })
        tasks = self.env['project.task'].search([('project_id', '=', self.fsm_project.id)])
        expected_tasks_count = len(tasks)
        self.assertEqual(task.worksheet_template_id, self.worksheet_template)

        service = self.env['product.product'].create({
            'name': 'Service',
            'type': 'service',
            'service_tracking': 'task_global_project',
            'project_id': self.fsm_project.id,
            'worksheet_template_id': self.second_worksheet_template.id,
        })
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_1.id,
            'order_line': [
                Command.create({
                    'name': 'description',
                    'product_id': service.id,
                    'product_uom_qty': 10.0,
                    'price_unit': 25.0,
                }),
            ],
        })
        sale_order.action_confirm()
        expected_tasks_count += 1
        tasks = self.env['project.task'].search([('project_id', '=', self.fsm_project.id)])
        self.assertEqual(len(tasks), expected_tasks_count)
        self.assertTrue(any(t.id != task.id and t.worksheet_template_id == self.second_worksheet_template for t in tasks))
