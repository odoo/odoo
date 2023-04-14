# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
from . import models

_logger = logging.getLogger(__name__)

def _l10n_it_edi_withholding_post_init(env):
    """ Existing companies that have the Italian Chart of Accounts set """
    template_code = 'it'
    ChartTemplate = env['account.chart.template']

    def filter_func(x):
        return x.template_code == template_code and x.model != 'template_data' and 'withholding' in x.func.__name__

    data = {
        model: ChartTemplate._parse_csv(template_code, model, module='l10n_it_edi_withholding')
        for _func, _code, model in ChartTemplate._get_template_functions_data(filter_func)
    }
    env['account.chart.template']._deref_account_tags(template_code, data['account.tax'])
    for company in env['res.company'].search([('chart_template', '=', template_code)]):
        _logger.info("Company %s already has the Italian localization installed, updating...", company.name)
        env['account.chart.template'].with_company(company)._load_data(data)
