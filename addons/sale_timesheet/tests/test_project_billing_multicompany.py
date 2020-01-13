# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.sale_timesheet.tests.common import TestCommonSaleTimesheetMultiCompanyNoChart

class TestProjectBillingMulticompany(TestCommonSaleTimesheetMultiCompanyNoChart):

    @classmethod
    def setUpClass(cls):
        super(TestProjectBillingMulticompany, cls).setUpClass()

        cls.setUpServiceProducts()

        Project = cls.env['project.project'].with_context(tracking_disable=True)
        cls.project_non_billable = Project.create({
            'name': "Non Billable Project",
            'allow_timesheets': True,
            'billable_type': 'no',
            'company_id': cls.env.company.id,
        })

    def test_makeBillable_multiCompany(self):
        wizard = self.env['project.create.sale.order'].with_context(allowed_company_ids=[self.company_B.id, self.env.company.id], company_id=self.company_B.id, active_id=self.project_non_billable.id, active_model='project.project').create({
            'product_id': self.product_delivery_timesheet3.id,  # product creates new Timesheet in new Project
            'price_unit': self.product_delivery_timesheet3.list_price,
            'billable_type': 'project_rate',
            'partner_id': self.partner_customer_usd.id,
        })

        action = wizard.action_create_sale_order()
        sale_order = self.env['sale.order'].browse(action['res_id'])

        self.assertEqual(sale_order.company_id.id, self.project_non_billable.company_id.id, "The company on the sale order should be the same as the one on the project")
