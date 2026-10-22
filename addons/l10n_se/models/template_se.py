# Part of Odoo. See LICENSE file for full copyright and licensing details.
"""Hidden base template shared by all Swedish charts of accounts.

Holds the data every Swedish chart needs regardless of size: taxes, tax groups,
fiscal positions and the company settings that do not depend on a specific
account. The visible charts (K1, K2 and their extensions) inherit from it.
Bank and cash accounts are not part of any chart: Odoo creates them from the
code prefixes below when bank and cash journals are created.
"""
from odoo import models

from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('se')
    def _get_se_template_data(self):
        return {
            'name': 'Sweden - Base',
            'visible': False,
            'code_digits': '4',
        }

    @template('se', 'res.company')
    def _get_se_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.se',
                'bank_account_code_prefix': '193',
                'cash_account_code_prefix': '191',
                'transfer_account_code_prefix': '194',
                'account_sale_tax_id': 'sale_tax_25_goods',
                'account_purchase_tax_id': 'purchase_tax_25_goods',
            },
        }
