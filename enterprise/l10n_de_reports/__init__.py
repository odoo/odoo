# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from odoo import api, SUPERUSER_ID


def _l10n_de_reports_post_init(env):
    for company in env['res.company'].search([('chart_template', '=', 'de_skr03')], order="parent_path"):
        ChartTemplate = env['account.chart.template'].with_company(company)
        ChartTemplate._load_data({
            'res.company': ChartTemplate._get_de_skr03_reports_res_company(company.chart_template),
        })

    for company in env['res.company'].search([('chart_template', '=', 'de_skr04')], order="parent_path"):
        ChartTemplate = env['account.chart.template'].with_company(company)
        ChartTemplate._load_data({
            'res.company': ChartTemplate._get_de_skr04_reports_res_company(company.chart_template),
        })
