# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.project.tests.test_project_profitability import TestProjectProfitabilityCommon


@tagged('-at_install', 'post_install')
class TestProjectAccountProfitability(TestProjectProfitabilityCommon):

    def test_project_profitability(self):
        """
            In this module, the project profitability should be computed while checking the AAL data.
            The Other Revenue and Other Cost sections should be displayed if some data are available.
        """
        project = self.env['project.project'].create({'name': 'new project'})
        project._create_analytic_account()
        self.assertDictEqual(
            project._get_profitability_items(False),
            self.project_profitability_items_empty,
            'The profitability data of the project should return no data and so 0 for each total amount.'
        )
        # Create a new company with the foreign currency.
        foreign_company = self.env['res.company'].create({'name': "My Test Company", 'currency_id': self.foreign_currency.id})

        # Create new AAL with the new company.
        self.env['account.analytic.line'].create([{
            'name': 'extra revenues 1',
            'account_id': project.analytic_account_id.id,
            'amount': 100,
            'company_id': foreign_company.id,
        }, {
            'name': 'extra costs 1',
            'account_id': project.analytic_account_id.id,
            'amount': -100,
            'company_id': foreign_company.id,
        }, {
            'name': 'extra revenues 2',
            'account_id': project.analytic_account_id.id,
            'amount': 50,
            'company_id': foreign_company.id,
        }, {
            'name': 'extra costs 2',
            'account_id': project.analytic_account_id.id,
            'amount': -50,
            'company_id': foreign_company.id,
        }])
        # Ensures that when all the AAL of the account belongs to another company, the total amount is still converted to the currency of the current active company
        self.assertDictEqual(
            project._get_profitability_items(False),
            {
                'revenues': {'data': [{'id': 'other_revenues_aal', 'sequence': self.project._get_profitability_sequence_per_invoice_type()['other_revenues_aal'],
                    'invoiced': 30.0, 'to_invoice': 0.0}], 'total': {'invoiced': 30.0, 'to_invoice': 0.0}},
                'costs': {'data': [{'id': 'other_costs_aal', 'sequence': self.project._get_profitability_sequence_per_invoice_type()['other_costs_aal'],
                    'billed': -30.0, 'to_bill': 0.0}], 'total': {'billed': -30.0, 'to_bill': 0.0}}
            },
            'The profitability data of the project should return the total amount for the revenues and costs from tha AAL of the account of the project.'
        )
        self.env['account.analytic.line'].create([{
            'name': 'extra revenues 1',
            'account_id': project.analytic_account_id.id,
            'amount': 100,
        }, {
            'name': 'extra costs 1',
            'account_id': project.analytic_account_id.id,
            'amount': -100,
        }, {
            'name': 'extra revenues 2',
            'account_id': project.analytic_account_id.id,
            'amount': 50,
        }, {
            'name': 'extra costs 2',
            'account_id': project.analytic_account_id.id,
            'amount': -50,
        }])
        # Ensures that multiple AAL from different companies are correctly computed for the project profitability
        self.assertDictEqual(
            project._get_profitability_items(False),
            {
                'revenues': {'data': [{'id': 'other_revenues_aal', 'sequence': project._get_profitability_sequence_per_invoice_type()['other_revenues_aal'],
                    'invoiced': 180.0, 'to_invoice': 0.0}], 'total': {'invoiced': 180.0, 'to_invoice': 0.0}},
                'costs': {'data': [{'id': 'other_costs_aal', 'sequence': project._get_profitability_sequence_per_invoice_type()['other_costs_aal'],
                    'billed': -180.0, 'to_bill': 0.0}], 'total': {'billed': -180.0, 'to_bill': 0.0}}
            },
            'The profitability data of the project should return the total amount for the revenues and costs from tha AAL of the account of the project.'
        )

        account_move = self.env['account.move'].create({
            "name": "I have 3 lines",
            "state": "draft",
            "partner_id": self.partner.id,
        })
        # Create new move line with analytic distribution
        account = self.env['account.account'].search([('company_id', '=', account_move.company_id.id)], limit=1)
        self.env['account.move.line'].create([{
            "analytic_distribution": {project.analytic_account_id.id: 100},
            "debit": 500,
            "move_id": account_move.id,
            "account_id": account.id
        }, {
            "analytic_distribution": {project.analytic_account_id.id: 100},
            "credit": 350,
            "move_id": account_move.id,
            "account_id": account.id
        }, {
            "credit": 150,
            "move_id": account_move.id,
            "account_id": account.id
        }])
        account_move.action_post()
        # Ensure that the move line have correctly generate an AAL, and that those AAL are correctly computed into the project profitability.
        self.assertDictEqual(
            project._get_profitability_items(False),
            {
                'revenues': {'data': [{'id': 'other_revenues', 'sequence': project._get_profitability_sequence_per_invoice_type()['other_revenues'],
                    'invoiced': 530.0, 'to_invoice': 0.0}], 'total': {'invoiced': 530.0, 'to_invoice': 0.0}},
                'costs': {'data': [{'id': 'other_costs', 'sequence': project._get_profitability_sequence_per_invoice_type()['other_costs'],
                    'billed': -680.0, 'to_bill': 0.0}], 'total': {'billed': -680.0, 'to_bill': 0.0}}
            },
            'The profitability data of the project should return the total amount for the revenues and costs from tha AAL of the account of the project.'
        )
