from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('sn')
    def _get_sn_template_data(self):
        return {
            'name': 'Syscohada for Sénégal',
            'parent': 'syscohada',
            'code_digits': '6',
        }

    @template('sn', 'res.company')
    def _get_sn_res_company(self):
        company_values = super()._get_syscohada_res_company()
        company_values[self.env.company.id].update(
            {
                'account_fiscal_country_id': 'base.sn',
                'account_sale_tax_id': 'tva_sale_18',
                'account_purchase_tax_id': 'tva_purchase_18',
            }
        )
        return company_values

    @template('sn', 'account.account')
    def _get_sn_account_account(self):
        return self._parse_csv('sn', 'account.account', module='l10n_syscohada')
