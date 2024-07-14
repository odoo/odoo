# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import wizard
from . import report


def _l10n_be_reports_post_init(env):
    for company in env['res.company'].search([('chart_template', '=', 'be_comp')]):
        ChartTemplate = env['account.chart.template'].with_company(company)
        company_data = ChartTemplate._get_be_comp_reports_res_company(company.chart_template)
        ChartTemplate._load_data({
            'res.company': company_data,
        })

    for company in env['res.company'].search([('chart_template', '=', 'be_asso')]):
        ChartTemplate = env['account.chart.template'].with_company(company)
        company_data = ChartTemplate._get_be_asso_reports_res_company(company.chart_template)
        ChartTemplate._load_data({
            'res.company': company_data,
        })
