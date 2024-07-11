from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('tg')
    def _get_tg_template_data(self):
        return {
            'name': 'Syscohada Chart of Accounts for Togo',
            'parent': 'syscohada',
            'code_digits': '6',
        }

    @template('tg', 'res.company')
    def _get_tg_res_company(self):
        company_values = super()._get_syscohada_res_company()
        company_values[self.env.company.id].update(
            {
                'account_fiscal_country_id': 'base.tg',
                'account_sale_tax_id': 'tva_sale_18',
                'account_purchase_tax_id': 'tva_purchase_good_18',
            }
        )
        return company_values

    @template('tg', 'account.account')
    def _get_tg_account_account(self):
        return self._parse_csv('tg', 'account.account', module='l10n_syscohada')
