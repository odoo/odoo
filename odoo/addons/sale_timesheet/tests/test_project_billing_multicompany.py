# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.sale_timesheet.tests.common import TestCommonSaleTimesheet
from odoo.tests import tagged


@tagged('-at_install', 'post_install')
class TestProjectBillingMulticompany(TestCommonSaleTimesheet):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        Project = cls.env['project.project'].with_context(tracking_disable=True)
        cls.project_non_billable = Project.create({
            'name': "Non Billable Project",
            'allow_timesheets': True,
            'allow_billable': True,
            'company_id': cls.env.company.id,
        })

    def test_makeBillable_multiCompany(self):
        wizard = self.env['project.create.sale.order'].with_context(allowed_company_ids=[self.company_data_2['company'].id, self.env.company.id], company_id=self.company_data_2['company'].id, active_id=self.project_non_billable.id, active_model='project.project').create({
            'line_ids': [(0, 0, {
                'product_id': self.product_delivery_timesheet3.id,  # product creates new Timesheet in new Project
                'price_unit': self.product_delivery_timesheet3.list_price
            })],
            'partner_id': self.partner_a.id,
        })

        action = wizard.action_create_sale_order()
        sale_order = self.env['sale.order'].browse(action['res_id'])

        self.assertEqual(sale_order.company_id.id, self.project_non_billable.company_id.id, "The company on the sale order should be the same as the one on the project")
