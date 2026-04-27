# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models, wizard


def _post_install_hook_configure_ecuadorian_data(env):
    # Force setup as l10n_ec_edi module was not installed at moment of creation of first company
    companies = env['res.company'].search([('account_fiscal_country_id.code', '=', 'EC'), ('chart_template', '!=', False)])

    env['account.chart.template']._l10n_ec_configure_ecuadorian_withhold_taxpayer_type(companies)
    env['account.chart.template']._l10n_ec_setup_profit_withhold_taxes(companies)
    env['account.chart.template']._l10n_ec_copy_taxsupport_codes_from_templates(companies)
    env['account.chart.template']._l10n_ec_configure_default_withhold_accounts(companies)
    env['account.chart.template']._l10n_ec_setup_edi_purchase_journal_account(companies)

    for company in companies:
        Template = env['account.chart.template'].with_company(company)  # Create journals of first company
        Template._load_data({
            'account.journal': Template._get_ec_edi_account_journal(),
        })

    company = env.ref('base.demo_company_ec', raise_if_not_found=False)  # demo company only
    if company:
        company._l10n_ec_set_taxpayer_type_for_demo()
