from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('bf')
    def _get_bf_template_data(self):
        return {
            'name': 'Syscohada for Burkina Faso',
            'parent': 'syscohada',
            'code_digits': '6',
        }

    @template('bf', 'res.company')
    def _get_bf_res_company(self):
        company_values = super()._get_syscohada_res_company()
        company_values[self.env.company.id].update(
            {
                'account_fiscal_country_id': 'base.bf',
                'account_sale_tax_id': 'tva_sale_18',
                'account_purchase_tax_id': 'tva_purchase_18',
            }
        )
        return company_values

    @template('bf', 'account.account')
    def _get_bf_account_account(self):
        return self._parse_csv('bf', 'account.account', module='l10n_syscohada')
