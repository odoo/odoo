from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('gq')
    def _get_gq_template_data(self):
        return {
            'name': 'Syscohada for Guinea Equatorial',
            'parent': 'syscohada',
            'code_digits': '6',
        }

    @template('gq', 'res.company')
    def _get_gq_res_company(self):
        company_values = super()._get_syscohada_res_company()
        company_values[self.env.company.id].update(
            {
                'account_fiscal_country_id': 'base.gq',
                'account_sale_tax_id': 'tva_sale_15',
                'account_purchase_tax_id': 'tva_purchase_15',
            }
        )
        return company_values

    @template('gq', 'account.account')
    def _get_gq_account_account(self):
        return self._parse_csv('gq', 'account.account', module='l10n_syscohada')
