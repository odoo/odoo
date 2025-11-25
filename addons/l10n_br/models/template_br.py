# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('br')
    def _get_br_template_data(self):
        return {
            'code_digits': '6',
            'property_account_receivable_id': 'account_template_101010401',
            'property_account_payable_id': 'account_template_201010301',
        }

    @template('br', 'res.company')
    def _get_br_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.br',
                'bank_account_code_prefix': '1.01.01.02.00',
                'cash_account_code_prefix': '1.01.01.01.00',
                'transfer_account_code_prefix': '1.01.01.12.00',
                'account_default_pos_receivable_account_id': 'account_template_101010402',
                'income_currency_exchange_account_id': 'br_3_01_01_05_01_47',
                'expense_currency_exchange_account_id': 'br_3_11_01_09_01_40',
                'account_journal_early_pay_discount_loss_account_id': 'account_template_31101010202',
                'account_journal_early_pay_discount_gain_account_id': 'account_template_30101050148',
                'account_sale_tax_id': 'tax_template_out_icms_interno17',
                'account_purchase_tax_id': 'tax_template_in_icms_interno17',
                'expense_account_id': 'account_template_30101030101',
                'income_account_id': 'account_template_30101010105',
                'account_stock_valuation_id': 'account_template_101030401',
            },
        }

    @template('br', 'account.journal')
    def _get_br_account_journal(self):
        return {
            'sale': {
                'l10n_br_invoice_serial': '1',
                'refund_sequence': False,
            },
        }

    @template('br', 'account.account')
    def _get_br_account_account(self):
        return {
            'account_template_101030401': {
                'account_stock_expense_id': 'account_template_30101030102',
                'account_stock_variation_id': 'account_template_101030405',
            },
            'account_template_102030102': {'asset_depreciation_account_id': 'account_template_102030131', 'asset_expense_account_id': 'account_template_30101070123'},
            'account_template_102030103': {'asset_depreciation_account_id': 'account_template_102030131', 'asset_expense_account_id': 'account_template_30101070123'},
            'account_template_102030105': {'asset_depreciation_account_id': 'account_template_102030231', 'asset_expense_account_id': 'account_template_30101090116'},
            'account_template_102030106': {'asset_depreciation_account_id': 'account_template_102030131', 'asset_expense_account_id': 'account_template_30101070123'},
            'account_template_102030107': {'asset_depreciation_account_id': 'account_template_102030131', 'asset_expense_account_id': 'account_template_30101070123'},
            'account_template_102030108': {'asset_depreciation_account_id': 'account_template_102030131', 'asset_expense_account_id': 'account_template_30101070123'},
            'account_template_102030109': {'asset_depreciation_account_id': 'account_template_102030131', 'asset_expense_account_id': 'account_template_30101070123'},
            'account_template_102030110': {'asset_depreciation_account_id': 'account_template_102030131', 'asset_expense_account_id': 'account_template_30101070123'},
            'account_template_102030111': {'asset_depreciation_account_id': 'account_template_102030132', 'asset_expense_account_id': 'account_template_30101070123'},
            'account_template_102030112': {'asset_depreciation_account_id': 'account_template_102030131', 'asset_expense_account_id': 'account_template_30101070123'},
            'account_template_102030113': {'asset_depreciation_account_id': 'account_template_102030131', 'asset_expense_account_id': 'account_template_30101070123'},
            'account_template_102030114': {'asset_depreciation_account_id': 'account_template_102030131', 'asset_expense_account_id': 'account_template_30101070123'},
            'account_template_102030115': {'asset_depreciation_account_id': 'account_template_102030131', 'asset_expense_account_id': 'account_template_30101070123'},
            'account_template_102030116': {'asset_depreciation_account_id': 'account_template_102030131', 'asset_expense_account_id': 'account_template_30101070123'},
            'account_template_102030128': {'asset_depreciation_account_id': 'account_template_102030131', 'asset_expense_account_id': 'account_template_30101070123'},
            'account_template_102030130': {'asset_depreciation_account_id': 'account_template_102030131', 'asset_expense_account_id': 'account_template_30101070123'},
            'account_template_102030155': {'asset_depreciation_account_id': 'account_template_102030131', 'asset_expense_account_id': 'account_template_30101070123'},
            'account_template_102030175': {'asset_depreciation_account_id': 'account_template_102030131', 'asset_expense_account_id': 'account_template_30101070123'},
            'account_template_102030176': {'asset_depreciation_account_id': 'account_template_102030131', 'asset_expense_account_id': 'account_template_30101070123'},
            'account_template_102030177': {'asset_depreciation_account_id': 'account_template_102030131', 'asset_expense_account_id': 'account_template_30101070123'},
            'account_template_102030190': {'asset_depreciation_account_id': 'account_template_102030131', 'asset_expense_account_id': 'account_template_30101070123'},
            'account_template_102030195': {'asset_depreciation_account_id': 'account_template_102030131', 'asset_expense_account_id': 'account_template_30101070123'},
            'account_template_102030201': {'asset_depreciation_account_id': 'account_template_102030131', 'asset_expense_account_id': 'account_template_30101070123'},
            'account_template_102030202': {'asset_depreciation_account_id': 'account_template_102030131', 'asset_expense_account_id': 'account_template_30101070123'},
            'account_template_102030203': {'asset_depreciation_account_id': 'account_template_102030131', 'asset_expense_account_id': 'account_template_30101070123'},
            'account_template_102030204': {'asset_depreciation_account_id': 'account_template_102030131', 'asset_expense_account_id': 'account_template_30101070123'},
            'account_template_102030205': {'asset_depreciation_account_id': 'account_template_102030131', 'asset_expense_account_id': 'account_template_30101070123'},
            'account_template_102030206': {'asset_depreciation_account_id': 'account_template_102030131', 'asset_expense_account_id': 'account_template_30101070123'},
            'account_template_102030209': {'asset_depreciation_account_id': 'account_template_102030231', 'asset_expense_account_id': 'account_template_30101090116'},
            'account_template_102030230': {'asset_depreciation_account_id': 'account_template_102030231', 'asset_expense_account_id': 'account_template_30101090116'},
            'account_template_102030255': {'asset_depreciation_account_id': 'account_template_102030231', 'asset_expense_account_id': 'account_template_30101090116'},
        }
