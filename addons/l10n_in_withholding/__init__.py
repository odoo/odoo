from . import models
from . import wizard

import logging

from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


def _l10n_in_withholding_post_init(env):
    """ Existing companies that have the Indian Chart of Accounts set """
    for company in env['res.company'].search([('chart_template', '=', 'in')]):
        _logger.info("Company %s already has the Indian localization installed, updating...", company.name)
        ChartTemplate = env['account.chart.template'].with_company(company)
        try:
            ChartTemplate._load_data({
                'account.account': ChartTemplate._get_in_withholding_account_account(),
            })
            company.l10n_in_withholding_account_id = env.ref('account.%i_p100595' % company.id)
        except ValidationError as e:
            _logger.warning("Error while updating Chart of Accounts for company %s: %s", company.name, e.args[0])
