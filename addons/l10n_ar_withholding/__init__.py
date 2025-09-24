# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import wizards
from . import demo

import logging

_logger = logging.getLogger(__name__)


def _l10n_ar_wth_post_init(env):
    """ Existing companies that have the Argentinean Chart of Accounts set """
    template_codes = ['ar_ri', 'ar_ex', 'ar_base']
    ar_companies = env['res.company'].search([('chart_template', 'in', template_codes), ('parent_id', '=', False)])
    for company in ar_companies:
        ChartTemplate = env['account.chart.template'].with_company(company)
        if company.chart_template == 'ar_ri' and env.ref('base.module_l10n_ar_withholding').demo:
            ChartTemplate._ar_withholding_copy_tax_demo()
