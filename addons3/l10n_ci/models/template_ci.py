from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('ci')
    def _get_ci_template_data(self):
        return {
            'name': 'Syscohada for Ivory Coast',
            'parent': 'syscohada',
            'code_digits': '6',
        }

    @template('ci', 'res.company')
    def _get_ci_res_company(self):
        company_values = super()._get_syscohada_res_company()
        company_values[self.env.company.id].update(
            {
                'account_fiscal_country_id': 'base.ci',
                'account_sale_tax_id': 'tva_sale_18',
                'account_purchase_tax_id': 'tva_purchase_18',
            }
        )
        return company_values

    @template('ci', 'account.account')
    def _get_ci_account_account(self):
        return self._parse_csv('ci', 'account.account', module='l10n_syscohada')
