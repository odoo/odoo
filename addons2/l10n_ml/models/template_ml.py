from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('ml')
    def _get_ml_template_data(self):
        return {
            'name': 'Syscohada for Tchad',
            'parent': 'syscohada',
            'code_digits': '6',
        }

    @template('ml', 'res.company')
    def _get_ml_res_company(self):
        company_values = super()._get_syscohada_res_company()
        company_values[self.env.company.id].update(
            {
                'account_fiscal_country_id': 'base.ml',
                'account_sale_tax_id': 'tva_sale_18',
                'account_purchase_tax_id': 'tva_purchase_18',
            }
        )
        return company_values

    @template('ml', 'account.account')
    def _get_ml_account_account(self):
        return self._parse_csv('ml', 'account.account', module='l10n_syscohada')
