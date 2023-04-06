# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
from . import models

_logger = logging.getLogger(__name__)

def _l10n_it_edi_withholding_post_init(env):
    """ Existing companies that have the Italian Chart of Accounts set """
    template_code = 'it'
    ChartTemplate = env['account.chart.template']

    data = {
        model: ChartTemplate._parse_csv(template_code, model, module='l10n_it_edi_withholding')
        for model in [
            'account.account',
            'account.tax.group',
            'account.tax',
            'account.fiscal.position',
        ]
    }

    ChartTemplate._deref_account_tags(template_code, data['account.tax'])
    for company in env['res.company'].search([('chart_template', '=', template_code)]):
        _logger.info("Company '%s' already has the Italian localization installed, updating...", company.name)
        chart_template = ChartTemplate.with_company(company)
        chart_template._load_data(data)

        # Demo PA partner needs Split Payment fiscal position. It ain't in the XML
        # because it has just been generated through the template in the lines above here.
        demo_company = env.ref('l10n_it.demo_company_it', raise_if_not_found=False)
        if company == demo_company:
            demo_pa_partner = env.ref('l10n_it_edi_withholding.demo_l10n_it_edi_withholding_partner_pa').with_company(company)
            demo_pa_partner.property_account_position_id = chart_template.ref('fiscal_position_split_payment')
