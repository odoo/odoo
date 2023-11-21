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
        for company in env['res.company'].search([('chart_template', '=', template_code)]):
            _logger.info("Company %s already has the Argentinean localization installed, updating...", company.name)
            company_chart_template = env['account.chart.template'].with_company(company)
            company_data = dict(data)
            company_chart_template._deref_account_tags(template_code, company_data['account.tax'])
            company_chart_template._load_data(company_data)
            company.l10n_ar_tax_base_account_id = env.ref('account.%i_base_tax_account' % company.id)

            if env.ref('base.module_l10n_ar_withholding').demo:
                env['account.chart.template']._post_load_demo_data(company)
