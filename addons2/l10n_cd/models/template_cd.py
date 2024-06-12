from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('cd')
    def _get_cd_template_data(self):
        return {
            'name': 'Syscohada Chart of Accounts for DRC',
            'parent': 'syscohada',
            'code_digits': '6',
        }

    @template('cd', 'res.company')
    def _get_cd_res_company(self):
        company_values = super()._get_syscohada_res_company()
        company_values[self.env.company.id].update(
            {
                'account_fiscal_country_id': 'base.cd',
                'account_sale_tax_id': 'tva_sale_16',
                'account_purchase_tax_id': 'tva_purchase_good_16',
            }
        )
        return company_values

    @template('cd', 'account.account')
    def _get_cd_account_account(self):
        return self._parse_csv('cd', 'account.account', module='l10n_syscohada')
