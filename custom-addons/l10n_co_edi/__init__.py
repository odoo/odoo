# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from . import models
from . import wizards


def _l10n_co_edi_post_init(env):
    for company in env['res.company'].search([('chart_template', '=', 'co')]):
        Template = env['account.chart.template'].with_company(company)
        Template._load_data({
            'account.tax': Template._get_co_edi_account_tax(),
            'account.tax.group': Template._get_co_edi_account_tax_group(),
        })
