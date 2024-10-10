# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('et')
    def _get_et_template_data(self):
        return {
            'code_digits': '6',
            'property_account_receivable_id': 'l10n_et2211',
            'property_account_payable_id': 'l10n_et3002',
        }

    @template('et', 'res.company')
    def _get_et_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.et',
                'bank_account_code_prefix': '211',
                'cash_account_code_prefix': '211',
                'transfer_account_code_prefix': '212',
                'account_default_pos_receivable_account_id': 'l10n_et2215',
                'income_currency_exchange_account_id': 'l10n_et6435',
                'expense_currency_exchange_account_id': 'l10n_et6436',
                'account_journal_early_pay_discount_loss_account_id': 'l10n_et626001',
                'account_journal_early_pay_discount_gain_account_id': 'l10n_et120001',
                'account_sale_tax_id': 'id_tax03',
                'account_purchase_tax_id': 'id_tax08',
                'expense_account_id': 'l10n_et2301',
                'income_account_id': 'l10n_et1100',
            },
        }
