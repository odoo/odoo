# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import wizards
from . import demo

import logging

_logger = logging.getLogger(__name__)


def _l10n_ar_withholding_post_init(env):
    """ Existing companies that have the Argentinean Chart of Accounts set """
    template_codes = ['ar_ri', 'ar_ex', 'ar_base']
    ar_companies = env['res.company'].search([('chart_template', 'in', template_codes), ('parent_id', '=', False)])
    for company in ar_companies:
        template_code = company.chart_template
        ChartTemplate = env['account.chart.template'].with_company(company)
        data = {
            model: ChartTemplate._parse_csv(template_code, model, module='l10n_ar_withholding')
            for model in [
                'account.account',
                'account.tax.group',
                'account.tax',
            ]
        }
        # Only update taxes if the related accounts exists.
        tax_keys = list(data['account.tax'].keys())
        print(" ---- tax_keys %s" % tax_keys)
        for tax_key in tax_keys:
            for line in data['account.tax'][tax_key].get('repartition_line_ids', []):
                if tax_account := line[-1].get('account_id'):
                    exist_account = env.ref('account.%i_%s' % (company.id, tax_account), raise_if_not_found=False)
                    if not exist_account:
                        data['account.tax'].pop(tax_key)
                        _logger.warning("We do not update the tax %s because the account %s does not exist", tax_key, tax_account)
                        break

        ChartTemplate._deref_account_tags(template_code, data['account.tax'])
        ChartTemplate._pre_reload_data(company, {}, data)
        ChartTemplate._load_data(data)
        company.l10n_ar_tax_base_account_id = ChartTemplate.ref('base_tax_account')

        if env.ref('base.module_l10n_ar_withholding').demo:
            env['account.chart.template']._post_load_demo_data(company)
