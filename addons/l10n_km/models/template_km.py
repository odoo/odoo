from odoo import models, _
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('km')
    def _get_km_template_data(self):
        return {
            'name': _('SYSCOHADA for Companies'),
            'parent': 'syscohada',
            'code_digits': '6',
        }

    @template('km', 'res.company')
    def _get_km_res_company(self):
        company_values = super()._get_syscohada_res_company()
        company_values[self.env.company.id].update(
            {
                'account_fiscal_country_id': 'base.km',
                'account_sale_tax_id': 'tva_sale_10',
                'account_purchase_tax_id': 'tva_purchase',
            }
        )
        return company_values

    @template('km', 'account.account')
    def _get_km_account_account(self):
        return self._parse_csv('km', 'account.account', module='l10n_syscohada')
