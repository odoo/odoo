# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
from . import models

_logger = logging.getLogger(__name__)

def _l10n_it_edi_withholding_post_init(env):
    """ Existing companies that have the Italian Chart of Accounts set """
    template_code = 'it'
    data = {
        model: env['account.chart.template']._parse_csv(template_code, model, module='l10n_it_edi_withholding')
        for model in [
            'account.account',
            'account.tax.group',
            'account.tax',
        ]
    }
    for company in env['res.company'].search([('chart_template', '=', template_code)]):
        _logger.info("Company %s already has the Italian localization installed, updating...", company.name)
        company_chart_template = env['account.chart.template'].with_company(company)
        company_data = dict(data)
        company_chart_template._deref_account_tags(template_code, company_data['account.tax'])
        company_chart_template._load_data(company_data)
