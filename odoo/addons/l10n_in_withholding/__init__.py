from . import models
from . import wizard

import logging

from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


def _l10n_in_withholding_post_init(env):
    """ Existing companies that have the Indian Chart of Accounts set """
    data = {
        model: env['account.chart.template']._parse_csv('in', model, module='l10n_in_withholding')
        for model in [
            'account.account',
            'account.tax',
        ]
    }
    for company in env['res.company'].search([('chart_template', '=', 'in'), ('parent_id', '=', False)]):
        _logger.info("Company %s already has the Indian localization installed, updating...", company.name)
        ChartTemplate = env['account.chart.template'].with_company(company)
        try:
            ChartTemplate._deref_account_tags('in', data['account.tax'])
            ChartTemplate._pre_reload_data(company, {}, data)
            ChartTemplate._load_data(data)
            company.l10n_in_withholding_account_id = env.ref('account.%i_p100595' % company.id)
        except ValidationError as e:
            _logger.warning("Error while updating Chart of Accounts for company %s: %s", company.name, e.args[0])
        tds_group_id = env.ref(f'account.{company.id}_tds_group', raise_if_not_found=False)
        if tds_group_id:
            tds_purchase_taxes = env['account.tax'].with_context(active_test=False).search([('tax_group_id', '=', tds_group_id.id), ('type_tax_use', '=', 'purchase')])
            tds_purchase_taxes.write({'l10n_in_tds_tax_type': 'purchase', 'type_tax_use': 'none'})
