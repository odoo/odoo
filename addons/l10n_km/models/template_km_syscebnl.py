from odoo import models, _
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('km_syscebnl')
    def _get_km_syscebnl_template_data(self):
        return {
            'name': _('SYSCEBNL for Associations'),
            'parent': 'syscebnl',
            'code_digits': '6',
        }

    @template('km_syscebnl', 'res.company')
    def _get_km_syscebnl_res_company(self):
        company_values = super()._get_syscebnl_res_company()
        company_values[self.env.company.id].update(
            {
                'account_fiscal_country_id': 'base.km',
                'account_sale_tax_id': 'syscebnl_tva_sale_10',
                'account_purchase_tax_id': 'syscebnl_tva_purchase',
            }
        )
        return company_values

    @template('km_syscebnl', 'account.account')
    def _get_km_syscebnl_account_account(self):
        return self._parse_csv('km_syscebnl', 'account.account', module='l10n_syscohada')
