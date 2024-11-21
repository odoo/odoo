from odoo import models, _
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('cf_syscebnl')
    def _get_cf_template_data(self):
        return {
            'name': _('SYSCEBNL for Associations'),
            'parent': 'syscebnl',
            'code_digits': '6',
        }

    @template('cf_syscebnl', 'res.company')
    def _get_cf_syscebnl_res_company(self):
        company_values = super()._get_syscebnl_res_company()
        company_values[self.env.company.id].update(
            {
                'account_fiscal_country_id': 'base.cf',
                'account_sale_tax_id': 'syscebnl_tva_sale_19',
                'account_purchase_tax_id': 'syscebnl_tva_purchase_19',
            }
        )
        return company_values

    @template('cf_syscebnl', 'account.account')
    def _get_cf_syscebnl_account_account(self):
        return self._parse_csv('cf_syscebnl', 'account.account', module='l10n_syscohada')
