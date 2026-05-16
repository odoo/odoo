# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('hk')
    def _get_hk_template_data(self):
        return {
            'property_account_receivable_id': 'l10n_hk_1240',
            'property_account_payable_id': 'l10n_hk_2211',
            'code_digits': '6',
        }

    @template('hk', 'res.company')
    def _get_hk_res_company(self):
        return {
            self.env.company.id: {
                'anglo_saxon_accounting': True,
                'account_fiscal_country_id': 'base.hk',
                'bank_account_code_prefix': '1200',
                'cash_account_code_prefix': '1210',
                'transfer_account_code_prefix': '111220',
                'account_default_pos_receivable_account_id': 'l10n_hk_1243',
                'income_currency_exchange_account_id': 'l10n_hk_4240',
                'expense_currency_exchange_account_id': 'l10n_hk_5240',
                'account_journal_early_pay_discount_loss_account_id': 'l10n_hk_5250',
                'account_journal_early_pay_discount_gain_account_id': 'l10n_hk_4250',
                'income_account_id': 'l10n_hk_41',
                'expense_account_id': 'l10n_hk_51',
                'account_stock_journal_id': 'inventory_valuation',
                'account_stock_valuation_id': 'l10n_hk_1270',
            },
        }

    @template('hk', 'account.account')
    def _get_hk_account_account(self):
        return {
            'l10n_hk_1270': {
                'account_stock_variation_id': 'l10n_hk_51',
            },
        }
