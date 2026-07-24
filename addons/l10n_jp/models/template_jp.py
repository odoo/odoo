from odoo import _, models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('jp')
    def _get_jp_template_data(self):
        return {
            'code_digits': '9',
        }

    @template('jp', 'res.company')
    def _get_jp_res_company(self):
        return {
            self.env.company.id: {
                'anglo_saxon_accounting': False,
                'account_fiscal_country_id': 'base.jp',
                'bank_account_code_prefix': '10A10002',
                'cash_account_code_prefix': '10A10002',
                'transfer_account_code_prefix': '10A10002',
                'receivable_account_id': 'l10n_jp_10A100090',
                'payable_account_id': 'l10n_jp_10B100040',
                'account_default_pos_receivable_account_id': 'l10n_jp_10A100670',
                'income_currency_exchange_account_id': 'l10n_jp_10D200100',
                'expense_currency_exchange_account_id': 'l10n_jp_10E300340',
                'account_journal_suspense_account_id': 'l10n_jp_10A100022',
                'account_journal_early_pay_discount_loss_account_id': 'l10n_jp_10E300040',
                'account_journal_early_pay_discount_gain_account_id': 'l10n_jp_10D200050',
                'income_account_id': 'l10n_jp_10D100030',
                'expense_account_id': 'l10n_jp_10E200200',
                'account_sale_tax_id': 'l10n_jp_tax_sale_10',
                'account_purchase_tax_id': 'l10n_jp_tax_purchase_10',
                'transfer_account_id': 'l10n_jp_10A100850',
                'account_stock_valuation_id': 'l10n_jp_10A100280',
                'default_cash_difference_expense_account_id': 'l10n_jp_10E300890',
                'default_cash_difference_income_account_id': 'l10n_jp_10D200720',
                'deferred_expense_account_id': 'l10n_jp_10A100540',
                'deferred_revenue_account_id': 'l10n_jp_10B100170',
                'account_production_wip_account_id': 'l10n_jp_10A100400',
                'account_production_wip_overhead_account_id': 'l10n_jp_10E110660',
            },
        }

    @template('jp', 'account.journal')
    def _get_jp_account_journal(self):
        return {
            'bank': {
                'default_account_id': 'l10n_jp_10A100024',
            },
            'cash': {
                'name': _('Cash'),
                'type': 'cash',
                'default_account_id': 'l10n_jp_10A100021',
            },
        }

    @template('jp', 'account.account')
    def _get_jp_account_account(self):
        return {
            'l10n_jp_10A100280': {'account_stock_variation_id': 'l10n_jp_10E100030'},
            'l10n_jp_10A100310': {'account_stock_variation_id': 'l10n_jp_10E100030'},
            'l10n_jp_10A210080': {'asset_depreciation_account_id': 'l10n_jp_10A210090', 'asset_expense_account_id': 'l10n_jp_10E200220'},
            'l10n_jp_10A210180': {'asset_depreciation_account_id': 'l10n_jp_10A210190', 'asset_expense_account_id': 'l10n_jp_10E200220'},
            'l10n_jp_10A210240': {'asset_depreciation_account_id': 'l10n_jp_10A210250', 'asset_expense_account_id': 'l10n_jp_10E200220'},
            'l10n_jp_10A210360': {'asset_depreciation_account_id': 'l10n_jp_10A210370', 'asset_expense_account_id': 'l10n_jp_10E200220'},
            'l10n_jp_10A210410': {'asset_depreciation_account_id': 'l10n_jp_10A210420', 'asset_expense_account_id': 'l10n_jp_10E200220'},
            'l10n_jp_10A210620': {'asset_depreciation_account_id': 'l10n_jp_10A210920', 'asset_expense_account_id': 'l10n_jp_10E200220'},
            'l10n_jp_10A220110': {'asset_depreciation_account_id': 'l10n_jp_10A220110', 'asset_expense_account_id': 'l10n_jp_10E200220'},
            'l10n_jp_10A220130': {'asset_depreciation_account_id': 'l10n_jp_10A220130', 'asset_expense_account_id': 'l10n_jp_10E200560'},
            'l10n_jp_10A300010': {'asset_depreciation_account_id': 'l10n_jp_10A300010', 'asset_expense_account_id': 'l10n_jp_10E300700'},
            'l10n_jp_10A300030': {'asset_depreciation_account_id': 'l10n_jp_10A300030', 'asset_expense_account_id': 'l10n_jp_10E200580'},
            'l10n_jp_10A300040': {'asset_depreciation_account_id': 'l10n_jp_10A300040', 'asset_expense_account_id': 'l10n_jp_10E300240'},
            'l10n_jp_10A300050': {'asset_depreciation_account_id': 'l10n_jp_10A300050', 'asset_expense_account_id': 'l10n_jp_10E300220'},
            'l10n_jp_10A300060': {'asset_depreciation_account_id': 'l10n_jp_10A300060', 'asset_expense_account_id': 'l10n_jp_10E200590'},
            'l10n_jp_10A300070': {'asset_depreciation_account_id': 'l10n_jp_10A300070', 'asset_expense_account_id': 'l10n_jp_10E300230'},
            'l10n_jp_10A220020': {'asset_depreciation_account_id': 'l10n_jp_10A220020', 'asset_expense_account_id': 'l10n_jp_10E200220'},
            'l10n_jp_10A220050': {'asset_depreciation_account_id': 'l10n_jp_10A220050', 'asset_expense_account_id': 'l10n_jp_10E200220'},
            'l10n_jp_10A220060': {'asset_depreciation_account_id': 'l10n_jp_10A220060', 'asset_expense_account_id': 'l10n_jp_10E200220'},
            'l10n_jp_10A220070': {'asset_depreciation_account_id': 'l10n_jp_10A220070', 'asset_expense_account_id': 'l10n_jp_10E200220'},
        }
