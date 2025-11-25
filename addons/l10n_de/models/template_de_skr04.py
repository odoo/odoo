# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, Command
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('de_skr04')
    def _get_de_skr04_template_data(self):
        return {
            'name': 'German chart of accounts SKR04',
            'code_digits': '4',
            'property_account_receivable_id': 'chart_skr04_1205',
            'property_account_payable_id': 'chart_skr04_3301',
        }

    @template('de_skr04', 'res.company')
    def _get_de_skr04_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.de',
                'bank_account_code_prefix': '180',
                'cash_account_code_prefix': '160',
                'transfer_account_code_prefix': '1460',
                'account_default_pos_receivable_account_id': 'chart_skr04_1206',
                'income_currency_exchange_account_id': 'chart_skr04_4840',
                'expense_currency_exchange_account_id': 'chart_skr04_6880',
                'account_journal_early_pay_discount_loss_account_id': 'chart_skr04_4730',
                'account_journal_early_pay_discount_gain_account_id': 'chart_skr04_5730',
                'default_cash_difference_income_account_id': 'chart_skr04_9991',
                'default_cash_difference_expense_account_id': 'chart_skr04_9994',
                'account_sale_tax_id': 'tax_ust_19_skr04',
                'account_purchase_tax_id': 'tax_vst_19_skr04',
                'expense_account_id': 'chart_skr04_5400',
                'income_account_id': 'chart_skr04_4400',
                'account_stock_valuation_id': 'chart_skr04_1000',
            },
        }

    @template('de_skr04', 'account.reconcile.model')
    def _get_de_skr04_reconcile_model(self):
        return {
            'reconcile_5731': {
                'name': 'Discount-EK-7%',
                'line_ids': [
                    Command.create({
                        'account_id': 'chart_skr04_5731',
                        'amount_type': 'percentage',
                        'tax_ids': [
                            Command.set([
                                'tax_vst_7_skr04',
                            ]),
                        ],
                        'amount_string': '100',
                        'label': 'Discount-EK-7%',
                    }),
                ],
            },
            'reconcile_5736': {
                'name': 'Discount-EK-19%',
                'line_ids': [
                    Command.create({
                        'account_id': 'chart_skr04_5736',
                        'amount_type': 'percentage',
                        'tax_ids': [
                            Command.set([
                                'tax_vst_19_skr04',
                            ]),
                        ],
                        'amount_string': '100',
                        'label': 'Discount-EK-19%',
                    }),
                ],
            },
            'reconcile_4731': {
                'name': 'Skonto-VK-7%',
                'line_ids': [
                    Command.create({
                        'account_id': 'chart_skr04_4731',
                        'amount_type': 'percentage',
                        'tax_ids': [
                            Command.set([
                                'tax_ust_7_skr04',
                            ]),
                        ],
                        'amount_string': '100',
                        'label': 'Discount-VK-7%',
                    }),
                ],
            },
            'reconcile_4736': {
                'name': 'Discount-VK-19%',
                'line_ids': [
                    Command.create({
                        'account_id': 'chart_skr04_4736',
                        'amount_type': 'percentage',
                        'tax_ids': [
                            Command.set([
                                'tax_ust_19_skr04',
                            ]),
                        ],
                        'amount_string': '100',
                        'label': 'Discount-VK-19%',
                    }),
                ],
            },
            'reconcile_6931': {
                'name': 'Loss of receivables-7%',
                'line_ids': [
                    Command.create({
                        'account_id': 'chart_skr04_6931',
                        'amount_type': 'percentage',
                        'tax_ids': [
                            Command.set([
                                'tax_ust_7_skr04',
                            ]),
                        ],
                        'amount_string': '100',
                        'label': 'Loss of receivables-7%',
                    }),
                ],
            },
            'reconcile_6936': {
                'name': 'Loss of receivables-19%',
                'line_ids': [
                    Command.create({
                        'account_id': 'chart_skr04_6936',
                        'amount_type': 'percentage',
                        'tax_ids': [
                            Command.set([
                                'tax_ust_19_skr04',
                            ]),
                        ],
                        'amount_string': '100',
                        'label': 'Loss of receivables-19%',
                    }),
                ],
            },
        }

    @template('de_skr04', 'account.account')
    def _get_de_skr04_account_account(self):
        return {
            'chart_skr04_1000': {
                'account_stock_expense_id': 'chart_skr04_5000',
                'account_stock_variation_id': 'chart_skr04_5880',
            },
            'chart_skr04_130': {
                'depreciation_model_id': 'asset_5_year_linear',
                'asset_depreciation_account_id': 'chart_skr04_134',
                'asset_expense_account_id': 'chart_skr04_6200',
            },
            'chart_skr04_135': {
                'depreciation_model_id': 'asset_1_year_linear',
                'asset_depreciation_account_id': 'chart_skr04_139',
                'asset_expense_account_id': 'chart_skr04_6200',
            },
            'chart_skr04_140': {
                'depreciation_model_id': 'asset_5_year_linear',
                'asset_depreciation_account_id': 'chart_skr04_149',
                'asset_expense_account_id': 'chart_skr04_6200',
            },
            'chart_skr04_150': {
                'depreciation_model_id': 'asset_15_year_linear',
                'asset_depreciation_account_id': 'chart_skr04_159',
                'asset_expense_account_id': 'chart_skr04_6200',
            },
            'chart_skr04_240': {
                'depreciation_model_id': 'asset_33_year_linear',
                'asset_depreciation_account_id': 'chart_skr04_249',
                'asset_expense_account_id': 'chart_skr04_6221',
            },
            'chart_skr04_250': {
                'depreciation_model_id': 'asset_33_year_linear',
                'asset_depreciation_account_id': 'chart_skr04_259',
                'asset_expense_account_id': 'chart_skr04_6221',
            },
            'chart_skr04_260': {
                'depreciation_model_id': 'asset_33_year_linear',
                'asset_depreciation_account_id': 'chart_skr04_249',
                'asset_expense_account_id': 'chart_skr04_6221',
            },
            'chart_skr04_270': {
                'depreciation_model_id': 'asset_20_year_linear',
                'asset_depreciation_account_id': 'chart_skr04_249',
                'asset_expense_account_id': 'chart_skr04_6221',
            },
            'chart_skr04_280': {
                'depreciation_model_id': 'asset_10_year_linear',
                'asset_depreciation_account_id': 'chart_skr04_249',
                'asset_expense_account_id': 'chart_skr04_6221',
            },
            'chart_skr04_285': {
                'depreciation_model_id': 'asset_19_year_linear',
                'asset_depreciation_account_id': 'chart_skr04_249',
                'asset_expense_account_id': 'chart_skr04_6221',
            },
            'chart_skr04_290': {
                'depreciation_model_id': 'asset_10_year_linear',
                'asset_depreciation_account_id': 'chart_skr04_249',
                'asset_expense_account_id': 'chart_skr04_6221',
            },
            'chart_skr04_300': {
                'depreciation_model_id': 'asset_50_year_linear',
                'asset_depreciation_account_id': 'chart_skr04_309',
                'asset_expense_account_id': 'chart_skr04_6221',
            },
            'chart_skr04_305': {
                'depreciation_model_id': 'asset_20_year_linear',
                'asset_depreciation_account_id': 'chart_skr04_309',
                'asset_expense_account_id': 'chart_skr04_6221',
            },
            'chart_skr04_310': {
                'depreciation_model_id': 'asset_10_year_linear',
                'asset_depreciation_account_id': 'chart_skr04_309',
                'asset_expense_account_id': 'chart_skr04_6221',
            },
            'chart_skr04_315': {
                'depreciation_model_id': 'asset_19_year_linear',
                'asset_depreciation_account_id': 'chart_skr04_309',
                'asset_expense_account_id': 'chart_skr04_6221',
            },
            'chart_skr04_320': {
                'depreciation_model_id': 'asset_10_year_linear',
                'asset_depreciation_account_id': 'chart_skr04_309',
                'asset_expense_account_id': 'chart_skr04_6221',
            },
            'chart_skr04_340': {
                'depreciation_model_id': 'asset_33_year_linear',
                'asset_depreciation_account_id': 'chart_skr04_349',
                'asset_expense_account_id': 'chart_skr04_6221',
            },
            'chart_skr04_350': {
                'depreciation_model_id': 'asset_33_year_linear',
                'asset_depreciation_account_id': 'chart_skr04_359',
                'asset_expense_account_id': 'chart_skr04_6221',
            },
            'chart_skr04_360': {
                'depreciation_model_id': 'asset_50_year_linear',
                'asset_depreciation_account_id': 'chart_skr04_369',
                'asset_expense_account_id': 'chart_skr04_6221',
            },
            'chart_skr04_370': {
                'depreciation_model_id': 'asset_33_year_linear',
                'asset_depreciation_account_id': 'chart_skr04_349',
                'asset_expense_account_id': 'chart_skr04_6221',
            },
            'chart_skr04_380': {
                'depreciation_model_id': 'asset_20_year_linear',
                'asset_depreciation_account_id': 'chart_skr04_349',
                'asset_expense_account_id': 'chart_skr04_6221',
            },
            'chart_skr04_390': {
                'depreciation_model_id': 'asset_10_year_linear',
                'asset_depreciation_account_id': 'chart_skr04_349',
                'asset_expense_account_id': 'chart_skr04_6221',
            },
            'chart_skr04_395': {
                'depreciation_model_id': 'asset_19_year_linear',
                'asset_depreciation_account_id': 'chart_skr04_349',
                'asset_expense_account_id': 'chart_skr04_6221',
            },
            'chart_skr04_398': {
                'depreciation_model_id': 'asset_10_year_linear',
                'asset_depreciation_account_id': 'chart_skr04_349',
                'asset_expense_account_id': 'chart_skr04_6221',
            },
            'chart_skr04_440': {
                'depreciation_model_id': 'asset_10_year_linear',
                'asset_depreciation_account_id': 'chart_skr04_449',
                'asset_expense_account_id': 'chart_skr04_6220',
            },
            'chart_skr04_450': {
                'depreciation_model_id': 'asset_14_year_linear',
                'asset_depreciation_account_id': 'chart_skr04_459',
                'asset_expense_account_id': 'chart_skr04_6220',
            },
            'chart_skr04_460': {
                'depreciation_model_id': 'asset_10_year_linear',
                'asset_depreciation_account_id': 'chart_skr04_469',
                'asset_expense_account_id': 'chart_skr04_6220',
            },
            'chart_skr04_470': {
                'depreciation_model_id': 'asset_10_year_linear',
                'asset_depreciation_account_id': 'chart_skr04_479',
                'asset_expense_account_id': 'chart_skr04_6220',
            },
            'chart_skr04_520': {
                'depreciation_model_id': 'asset_6_year_linear',
                'asset_depreciation_account_id': 'chart_skr04_529',
                'asset_expense_account_id': 'chart_skr04_6222',
            },
            'chart_skr04_540': {
                'depreciation_model_id': 'asset_9_year_linear',
                'asset_depreciation_account_id': 'chart_skr04_549',
                'asset_expense_account_id': 'chart_skr04_6222',
            },
            'chart_skr04_560': {
                'depreciation_model_id': 'asset_7_year_linear',
                'asset_depreciation_account_id': 'chart_skr04_569',
                'asset_expense_account_id': 'chart_skr04_6222',
            },
            'chart_skr04_5601': {
                'depreciation_model_id': 'asset_7_year_linear',
                'asset_depreciation_account_id': 'chart_skr04_569',
                'asset_expense_account_id': 'chart_skr04_6222',
            },
            'chart_skr04_5602': {
                'depreciation_model_id': 'asset_3_year_linear',
                'asset_depreciation_account_id': 'chart_skr04_569',
                'asset_expense_account_id': 'chart_skr04_6222',
            },
            'chart_skr04_5603': {
                'depreciation_model_id': 'asset_8_year_linear',
                'asset_depreciation_account_id': 'chart_skr04_569',
                'asset_expense_account_id': 'chart_skr04_6220',
            },
            'chart_skr04_5604': {
                'depreciation_model_id': 'asset_7_year_linear',
                'asset_depreciation_account_id': 'chart_skr04_569',
                'asset_expense_account_id': 'chart_skr04_6220',
            },
            'chart_skr04_620': {
                'depreciation_model_id': 'asset_5_year_linear',
                'asset_depreciation_account_id': 'chart_skr04_629',
                'asset_expense_account_id': 'chart_skr04_6220',
            },
            'chart_skr04_635': {
                'depreciation_model_id': 'asset_1_year_linear',
                'asset_depreciation_account_id': 'chart_skr04_639',
                'asset_expense_account_id': 'chart_skr04_6220',
            },
            'chart_skr04_6351': {
                'depreciation_model_id': 'asset_5_year_linear',
                'asset_depreciation_account_id': 'chart_skr04_639',
                'asset_expense_account_id': 'chart_skr04_6220',
            },
            'chart_skr04_6352': {
                'depreciation_model_id': 'asset_7_year_linear',
                'asset_depreciation_account_id': 'chart_skr04_639',
                'asset_expense_account_id': 'chart_skr04_6220',
            },
            'chart_skr04_640': {
                'depreciation_model_id': 'asset_8_year_linear',
                'asset_depreciation_account_id': 'chart_skr04_649',
                'asset_expense_account_id': 'chart_skr04_6220',
            },
            'chart_skr04_650': {
                'depreciation_model_id': 'asset_13_year_linear',
                'asset_depreciation_account_id': 'chart_skr04_659',
                'asset_expense_account_id': 'chart_skr04_6220',
            },
            'chart_skr04_660': {
                'depreciation_model_id': 'asset_5_year_linear',
                'asset_depreciation_account_id': 'chart_skr04_669',
                'asset_expense_account_id': 'chart_skr04_6220',
            },
            'chart_skr04_670': {
                'depreciation_model_id': 'asset_1_year_linear',
                'asset_depreciation_account_id': 'chart_skr04_674',
                'asset_expense_account_id': 'chart_skr04_6220',
            },
            'chart_skr04_675': {
                'depreciation_model_id': 'asset_5_year_linear',
                'asset_depreciation_account_id': 'chart_skr04_679',
                'asset_expense_account_id': 'chart_skr04_6220',
            },
        }
