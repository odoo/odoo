#-*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import report
from . import wizard

from collections import defaultdict
from odoo import api, SUPERUSER_ID, _

def _hr_payroll_account_post_init(env):
    for company in env['res.company'].search([('chart_template', '!=', False)], order="parent_path"):
        ChartTemplate = env['account.chart.template'].with_company(company)
        ChartTemplate._load_data({
            'account.journal': ChartTemplate._get_payroll_account_journal(company.chart_template),
            'hr.payroll.structure': ChartTemplate._get_payroll_structure(company.chart_template),
        })

def _salaries_account_journal_pre_init(env):
    """
        This pre-init hook will check if there is existing "SLR" journal and modify it to keep the code "SLR" free,
        so that we can add an "SLR" journal in the post init hook
    """
    companies = env['res.company'].search([])

    env.cr.execute("""SELECT company_id, code, id FROM account_journal WHERE company_id in %s AND code LIKE %s""", [tuple(companies.ids), 'SLR%'])
    slr_journals_per_company = defaultdict(dict)
    for company_id, code, journal_id in env.cr.fetchall():
        slr_journals_per_company[company_id].update({code: journal_id})

    if slr_journals_per_company:
        to_change = list()
        for company_id, slr_journals in slr_journals_per_company.items():
            copy_code = f"SLR{next(i for i in range(len(slr_journals) + 1) if f'SLR{i}' not in slr_journals.keys())}"
            to_change.append((copy_code, slr_journals.get('SLR'), company_id))

        for copy_code, journal, company_id in to_change:
            env.cr.execute("""UPDATE account_journal SET code = %s WHERE id = %s AND company_id = %s""", [copy_code, journal, company_id])
