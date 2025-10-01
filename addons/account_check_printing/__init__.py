# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from . import models
from . import wizard


def _post_init_hook(env):

    for company in env['res.company'].search([('parent_id', '=', False)]):
        ChartTemplate = env['account.chart.template'].with_company(company)
        ChartTemplate._load_data({
            'account.payment.method': ChartTemplate._get_check_printing_payment_method(company.chart_template)
        })
