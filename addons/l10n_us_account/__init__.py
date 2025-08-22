# Part of Odoo. See LICENSE file for full copyright and licensing details.

# The purpose of l10n_us_account is to automatically trigger the installation of l10n_us for the new US databases
# Also, l10n_us_account should contains all the accounting-related dependencies of US localization package
from . import models


def _l10n_us_account_post_init(env):
    for company in env['res.company'].search([('chart_template', '=', 'generic_coa'), ('account_fiscal_country_id.code', '=', 'US')], order="parent_path"):
        Template = env['account.chart.template'].with_company(company)
        Template._load_data({
            'account.tax': Template._get_us_account_tax(),
            'account.tax.group': Template._get_us_account_tax_group(),
            'res.company': Template._get_us_default_taxes_res_company(),
        })
