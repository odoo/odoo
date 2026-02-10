from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('mk')
    def _get_mk_template_data(self):
        return {
            'property_account_receivable_id': 'l10n_mk_account_120',
            'property_account_payable_id': 'l10n_mk_account_220',
            'code_digits': '6',
            'use_storno_accounting': True,
        }

    @template('mk', 'res.company')
    def _get_mk_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.mk',
                'income_account_id': 'l10n_mk_account_730',
                'expense_account_id': 'l10n_mk_account_701',
            },
        }
