# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('sg')
    def _get_sg_template_data(self):
        return {
            'code_digits': '6',
        }

    @template('sg', 'res.company')
    def _get_sg_res_company(self):
        return {
            self.env.company.id: {
                'anglo_saxon_accounting': True,
                'account_fiscal_country_id': 'base.sg',
                'bank_account_code_prefix': '2101',
                'cash_account_code_prefix': '2103',
                'transfer_account_code_prefix': '2108',
                'account_default_pos_receivable_account_id': 'l10n_sg_220200',
                'income_currency_exchange_account_id': 'l10n_sg_520400',
                'expense_currency_exchange_account_id': 'l10n_sg_660500',
                'account_journal_suspense_account_id': 'l10n_sg_210500',
                'transfer_account_id': 'l10n_sg_210800',
                'account_journal_early_pay_discount_loss_account_id': 'l10n_sg_660900',
                'account_journal_early_pay_discount_gain_account_id': 'l10n_sg_521100',
                'default_cash_difference_income_account_id': 'l10n_sg_999001',
                'default_cash_difference_expense_account_id': 'l10n_sg_999002',
                'account_sale_tax_id': 'sg_sale_tax_sr_9',
                'account_purchase_tax_id': 'sg_purchase_tax_tx8_9',
                'expense_account_id': 'l10n_sg_610500',
                'income_account_id': 'l10n_sg_510000',
                'receivable_account_id': 'l10n_sg_220100',
                'payable_account_id': 'l10n_sg_430100',
                'account_stock_valuation_id': 'l10n_sg_240400',
            },
        }

    def _get_account_parent_xmlid(self, code_prefix, template_code):
        if template_code == 'sg':
            return {
                '2101': 'l10n_sg_210000',
                '2103': 'l10n_sg_210000',
                '2108': 'l10n_sg_210000',
            }.get(code_prefix)
        return super()._get_account_parent_xmlid(code_prefix, template_code)

    @template('sg', 'account.journal')
    def _get_sg_account_journal(self):
        return {
            'bank': {
                'default_account_id': 'l10n_sg_210100',
            },
        }

    @template('sg', 'account.account')
    def _get_sg_account_account(self):
        return {
            'l10n_sg_240400': {
                'account_stock_variation_id': 'l10n_sg_611200',
            },
            'l10n_sg_110200': {'asset_depreciation_account_id': 'l10n_sg_110210', 'asset_expense_account_id': 'l10n_sg_700100'},
            'l10n_sg_110300': {'asset_depreciation_account_id': 'l10n_sg_110310', 'asset_expense_account_id': 'l10n_sg_700200'},
            'l10n_sg_110400': {'asset_depreciation_account_id': 'l10n_sg_110410', 'asset_expense_account_id': 'l10n_sg_700300'},
            'l10n_sg_110500': {'asset_depreciation_account_id': 'l10n_sg_110510', 'asset_expense_account_id': 'l10n_sg_700400'},
            'l10n_sg_110600': {'asset_depreciation_account_id': 'l10n_sg_110610', 'asset_expense_account_id': 'l10n_sg_700500'},
            'l10n_sg_110700': {'asset_depreciation_account_id': 'l10n_sg_110710', 'asset_expense_account_id': 'l10n_sg_700600'},
            'l10n_sg_110800': {'asset_depreciation_account_id': 'l10n_sg_110810', 'asset_expense_account_id': 'l10n_sg_700700'},
            'l10n_sg_120100': {'asset_depreciation_account_id': 'l10n_sg_120200', 'asset_expense_account_id': 'l10n_sg_700800'},
            'l10n_sg_120300': {'asset_depreciation_account_id': 'l10n_sg_120400', 'asset_expense_account_id': 'l10n_sg_700900'},
        }
