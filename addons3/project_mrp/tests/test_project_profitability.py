# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.project.tests.test_project_profitability import TestProjectProfitabilityCommon

@tagged('-at_install', 'post_install')
class TestSaleProjectProfitabilityMrp(TestProjectProfitabilityCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.foreign_company = cls.env['res.company'].create(
            {'name': "My Test Company", 'currency_id': cls.foreign_currency.id})

    def test_profitability_mrp_project(self):
        """ This test ensures that when mrp are linked to the project, the total is correctly computed for the project profitability. """

        project = self.env['project.project'].create({'name': 'new project'})
        project._create_analytic_account()
        account = project.analytic_account_id
        # creates the aal for the project
        self.env['account.analytic.line'].create([{
            'name': 'line 1',
            'account_id': account.id,
            'category': 'manufacturing_order',
            'company_id': self.foreign_company.id,
            'amount': '500',
            'unit_amount': '1',
        }, {
            'name': 'line 2',
            'account_id': account.id,
            'category': 'manufacturing_order',
            'company_id': self.foreign_company.id,
            'amount': '100',
            'unit_amount': '1',
        }])
        # Ensures that if none of the mrp linked to the project have the same company as the current active company, the total is still converted into the current active company.
        self.assertDictEqual(project._get_profitability_items(with_action=False), {
            'revenues': {'data': [], 'total': {'invoiced': 0.0, 'to_invoice': 0.0}},
            'costs': {'data': [{'id': 'manufacturing_order', 'sequence': 12, 'billed': 120.0, 'to_bill': 0.0}], 'total': {'billed': 120.0, 'to_bill': 0.0}}
        })
        self.env['account.analytic.line'].create([{
            'name': 'line 3',
            'account_id': account.id,
            'category': 'manufacturing_order',
            'company_id': self.env.company.id,
            'amount': '500',
            'unit_amount': '1',
        }, {
            'name': 'line 4',
            'account_id': account.id,
            'category': 'manufacturing_order',
            'company_id': self.env.company.id,
            'amount': '200',
            'unit_amount': '1',
        }])
        # Adds mrp AAL with the default company
        self.assertDictEqual(project._get_profitability_items(with_action=False), {
                'revenues': {'data': [], 'total': {'invoiced': 0.0, 'to_invoice': 0.0}},
                'costs': {'data': [{'id': 'manufacturing_order', 'sequence': 12, 'billed': 820.0, 'to_bill': 0.0}], 'total': {'billed': 820.0, 'to_bill': 0.0}}
        })
