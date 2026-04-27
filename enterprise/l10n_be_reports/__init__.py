# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import wizard
from . import report
from ..account_loans import _account_loans_import_loan_demo


def _l10n_be_reports_post_init(env):
    for company in env['res.company'].search([('chart_template', '=', 'be_comp')], order="parent_path"):
        ChartTemplate = env['account.chart.template'].with_company(company)
        company_data = ChartTemplate._get_be_comp_reports_res_company(company.chart_template)
        ChartTemplate._load_data({
            'res.company': company_data,
        })

    for company in env['res.company'].search([('chart_template', '=', 'be_asso')], order="parent_path"):
        ChartTemplate = env['account.chart.template'].with_company(company)
        company_data = ChartTemplate._get_be_asso_reports_res_company(company.chart_template)
        ChartTemplate._load_data({
            'res.company': company_data,
        })

    # If in demo, import the demo amortization schedule in the loan
    if env['ir.module.module'].search_count([('demo', '=', True)]):
        for company in env['res.company'].search([('chart_template', 'in', ('be_comp', 'be_asso'))]):
            env.company = company
            asset_group = env['account.asset.group'].create({
                'name': 'Odoo BE Office',
            })
            journal = env['account.journal'].search([('code','=', 'LOAN')], limit = 1)
            if not journal:
                journal = env['account.journal'].create({
                    'name': 'Journal Loan Demo BE',
                    'type': 'general',
                    'code': 'LOAN',
                })
            for i, file_type in enumerate(['csv', 'xlsx']):
                _account_loans_import_loan_demo(
                    env,
                    env['account.loan'].create({
                        'name': f'Loan Demo BE {i + 1}',
                        'journal_id': journal.id,
                        'asset_group_id': asset_group.id,
                        'long_term_account_id': env['account.chart.template'].with_company(company).ref('a1730').id,
                        'short_term_account_id': env['account.chart.template'].with_company(company).ref('a4230').id,
                        'expense_account_id': env['account.chart.template'].with_company(company).ref('a6500').id,
                    }),
                    env.ref(f'account_loans.account_loans_loan_demo_file_{file_type}'),
                )
