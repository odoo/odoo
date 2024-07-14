# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models

def _update_saft_fields_on_taxes(env):
    for company in env['res.company'].search([('chart_template', '=', 'ro')]):
        Template = env['account.chart.template'].with_company(company)
        Template._load_data({'account.tax': Template._get_ro_saft_account_tax()})
