# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import wizards
from . import demo

import logging

_logger = logging.getLogger(__name__)


def _l10n_ar_withholding_post_init(env):
    """ Existing companies that have the Argentinean Chart of Accounts set """
    template_codes = ['ar_ri', 'ar_ex', 'ar_base']
    for template_code in template_codes:
        data = {
            model: env['account.chart.template']._parse_csv(template_code, model, module='l10n_ar_withholding')
            for model in [
                'account.account',
                'account.tax.group',
                'account.tax',
            ]
        }
        env['account.chart.template']._deref_account_tags(template_code, data['account.tax'])
        for company in env['res.company'].search([('chart_template', '=', template_code)]):
            _logger.info("Company %s already has the Argentinean localization installed, updating...", company.name)
            env['account.chart.template'].with_company(company)._load_data(data)
            env['account.chart.template'].with_company(company)._post_load_data(template_code, company, data)

        if template_code in ['ar_ri'] and env.ref('base.module_l10n_ar_withholding').demo:
            env['account.chart.template']._post_load_demo_data(company)
