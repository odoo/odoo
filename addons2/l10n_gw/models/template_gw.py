from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('gw')
    def _get_gw_template_data(self):
        return {
            'name': 'Syscohada for Guinea-Bissau',
            'parent': 'syscohada',
            'code_digits': '6',
        }

    @template('gw', 'res.company')
    def _get_gw_res_company(self):
        company_values = super()._get_syscohada_res_company()
        company_values[self.env.company.id].update(
            {
                'account_fiscal_country_id': 'base.gw',
                'account_sale_tax_id': 'tva_sale_5',
                'account_purchase_tax_id': 'tva_purchase_5',
            }
        )
        return company_values

    @template('gw', 'account.account')
    def _get_gw_account_account(self):
        return self._parse_csv('gw', 'account.account', module='l10n_syscohada')
