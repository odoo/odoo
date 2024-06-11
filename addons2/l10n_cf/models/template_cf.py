from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('cf')
    def _get_cf_template_data(self):
        return {
            'name': 'Syscohada for Central African Republic',
            'parent': 'syscohada',
            'code_digits': '6',
        }

    @template('cf', 'res.company')
    def _get_cf_res_company(self):
        company_values = super()._get_syscohada_res_company()
        company_values[self.env.company.id].update(
            {
                'account_fiscal_country_id': 'base.cf',
                'account_sale_tax_id': 'tva_sale_19',
                'account_purchase_tax_id': 'tva_purchase_19',
            }
        )
        return company_values

    @template('cf', 'account.account')
    def _get_cf_account_account(self):
        return self._parse_csv('cf', 'account.account', module='l10n_syscohada')

