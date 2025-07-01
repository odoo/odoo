# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
from . import models

_logger = logging.getLogger(__name__)

def _l10n_it_edi_withholding_post_init(env):
    """ Existing companies that have the Italian Chart of Accounts set """
    for company in env['res.company'].search([('chart_template', '=', 'it') , ('parent_id', '=', False)]):
        _logger.info("Company %s already has the Italian localization installed, updating...", company.name)
        ChartTemplate = env['account.chart.template'].with_company(company)
        ChartTemplate._load_data({
            'account.account': ChartTemplate._get_it_withholding_account_account(),
            'account.tax': {
                xml_id: data
                for xml_id, data in ChartTemplate._get_it_withholding_account_tax().items()
                if not env.ref(f"account.{company.id}_{xml_id}", raise_if_not_found=False)
            },
            'account.tax.group': ChartTemplate._get_it_withholding_account_tax_group(),
        })
