from odoo import models, _
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('cd')
    def _get_cd_template_data(self):
        return {
            'name': _('SYSCOHADA for Companies'),
            'parent': 'syscohada',
            'code_digits': '6',
        }

    @template('cd', 'res.company')
    def _get_cd_res_company(self):
        company_values = super()._get_syscohada_res_company()
        company_values[self.env.company.id].update(
            {
                'account_fiscal_country_id': 'base.cd',
                'account_sale_tax_id': 'tva_sale_16',
                'account_purchase_tax_id': 'tva_purchase_good_16',
                'account_stock_journal_id': 'inventory_valuation',
                'account_stock_valuation_id': 'pcg_382',
            }
        )
        return company_values

    @template('cd', 'account.account')
    def _get_cd_account_account(self):
        account_values = self._parse_csv('cd', 'account.account', module='l10n_syscohada')
        account_values['pcg_382'].update({
            'account_stock_expense_id': 'pcg_6021',
            'account_stock_variation_id': 'pcg_6032',
        })
        return account_values
