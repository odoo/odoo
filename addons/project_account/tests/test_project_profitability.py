# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.project.tests.test_project_profitability import TestProjectProfitabilityCommon


@tagged('-at_install', 'post_install')
class TestProjectPurchaseProfitability(TestProjectProfitabilityCommon):

    def test_project_profitability(self):
        """
            In this module, the project profitability should be computed while checking the AAL data.
            The Other Revenue and Other Cost sections should be displayed if some data are available.
        """
        self.assertDictEqual(
            self.project._get_profitability_items(False),
            self.project_profitability_items_empty,
            'The profitability data of the project should return no data and so 0 for each total amount.'
        )
        self.env['account.analytic.line'].create([{
            'name': 'extra revenues 1',
            'account_id': self.project.analytic_account_id.id,
            'amount': 100,
        }, {
            'name': 'extra costs 1',
            'account_id': self.project.analytic_account_id.id,
            'amount': -100,
        }, {
            'name': 'extra revenues 2',
            'account_id': self.project.analytic_account_id.id,
            'amount': 50,
        }, {
            'name': 'extra costs 2',
            'account_id': self.project.analytic_account_id.id,
            'amount': -50,
        }])

        self.assertDictEqual(
            self.project._get_profitability_items(False),
            {
                'revenues': {'data': [{'id': 'other_revenues', 'sequence': self.project._get_profitability_sequence_per_invoice_type()['other_revenues'],
                    'invoiced': 150.0, 'to_invoice': 0.0}], 'total': {'invoiced': 150.0, 'to_invoice': 0.0}},
                'costs': {'data': [{'id': 'other_costs', 'sequence': self.project._get_profitability_sequence_per_invoice_type()['other_costs'],
                    'billed': -150.0, 'to_bill': 0.0}], 'total': {'billed': -150.0, 'to_bill': 0.0}}
            },
            'The profitability data of the project should return the total amount for the revenues and costs from tha AAL of the account of the project.'
        )
