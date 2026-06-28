from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('mk')
    def _get_mk_template_data(self):
        return {
            'code_digits': '6',
        }

    @template('mk', 'res.company')
    def _get_mk_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.mk',
                'income_account_id': 'l10n_mk_account_730',
                'expense_account_id': 'l10n_mk_account_701',
                'receivable_account_id': 'l10n_mk_account_120',
                'payable_account_id': 'l10n_mk_account_220',
            },
        }
