from odoo import models

from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('np')
    def _get_np_template_data(self):
        return {
            'code_digits': '6',
        }

    @template('np', 'res.company')
    def _get_np_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.np',
                'bank_account_code_prefix': '1014',
                'cash_account_code_prefix': '1015',
                'transfer_account_code_prefix': '1017',
                'receivable_account_id': 'l10n_np_1210',
                'payable_account_id': 'l10n_np_2110',
                'income_account_id': 'l10n_np_4000',
                'expense_account_id': 'l10n_np_6000',
                'account_default_pos_receivable_account_id': 'l10n_np_1210',
            },
        }
