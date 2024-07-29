from odoo import models, _
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('cd_syscebnl')
    def _get_cd_syscebnl_template_data(self):
        return {
            'name': _('SYSCEBNL for Associations'),
            'parent': 'syscebnl',
            'code_digits': '6',
        }

    @template('cd_syscebnl', 'res.company')
    def _get_cd_syscebnl_res_company(self):
        company_values = super()._get_syscebnl_res_company()
        company_values[self.env.company.id].update(
            {
                'account_fiscal_country_id': 'base.cd',
                'account_sale_tax_id': 'syscebnl_tva_sale_16',
                'account_purchase_tax_id': 'syscebnl_tva_purchase_good_16',
            }
        )
        return company_values

    @template('cd_syscebnl', 'account.account')
    def _get_cd_syscebnl_account_account(self):
        return self._parse_csv('cd_syscebnl', 'account.account', module='l10n_syscohada')
