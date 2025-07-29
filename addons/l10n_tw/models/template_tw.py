# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('tw')
    def _get_tw_template_data(self):
        return {
            'code_digits': '4',
            'property_account_receivable_id': 'l10n_tw_account_1156',
            'property_account_payable_id': 'l10n_tw_account_2171',
            'property_stock_account_production_cost_id': 'l10n_tw_account_5101',
        }

    @template('tw', 'res.company')
    def _get_tw_res_company(self):
        return {
            self.env.company.id: {
                'anglo_saxon_accounting': True,
                'account_fiscal_country_id': 'base.tw',
                'bank_account_code_prefix': '1100',
                'cash_account_code_prefix': '1101',
                'transfer_account_code_prefix': '1103',
                'account_journal_suspense_account_id': 'l10n_tw_account_1102',
                'transfer_account_id': 'l10n_tw_account_1103',
                'deferred_expense_account_id': 'l10n_tw_account_1411',
                'deferred_revenue_account_id': 'l10n_tw_account_2141',
                'account_default_pos_receivable_account_id': 'l10n_tw_account_1157',
                'income_currency_exchange_account_id': 'l10n_tw_account_7171',
                'expense_currency_exchange_account_id': 'l10n_tw_account_7541',
                'account_journal_early_pay_discount_loss_account_id': 'l10n_tw_account_4821',
                'account_journal_early_pay_discount_gain_account_id': 'l10n_tw_account_7191',
                'default_cash_difference_income_account_id': 'l10n_tw_account_7181',
                'default_cash_difference_expense_account_id': 'l10n_tw_account_7561',
                'account_sale_tax_id': 'tw_tax_sale_5',
                'account_purchase_tax_id': 'tw_tax_purchase_5',
                'expense_account_id': 'l10n_tw_account_5601',
                'income_account_id': 'l10n_tw_account_4111',
                'account_production_wip_account_id': 'l10n_tw_account_1314',
                'account_production_wip_overhead_account_id': 'l10n_tw_account_5601',
                'tax_calculation_rounding_method': 'round_globally',
            },
        }

    @template('tw', 'account.journal')
    def _get_tw_account_journal(self):
        return {
            'bank': {
                'default_account_id': 'l10n_tw_account_1100',
            },
            'cash': {
                'name': self.env._("Cash"),
                'type': 'cash',
                'default_account_id': 'l10n_tw_account_1101',
            },
        }
