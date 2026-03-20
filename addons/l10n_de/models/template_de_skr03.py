# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, Command
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('de_skr03')
    def _get_de_skr03_template_data(self):
        return {
            'code_digits': '4',
            'property_account_receivable_id': 'account_1410',
            'property_account_payable_id': 'account_1610',
            'property_stock_valuation_account_id': 'account_3960',
            'name': 'German Chart of Accounts SKR03',
        }

    @template('de_skr03', 'res.company')
    def _get_de_skr03_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.de',
                'bank_account_code_prefix': '120',
                'cash_account_code_prefix': '100',
                'transfer_account_code_prefix': '1360',
                'account_default_pos_receivable_account_id': 'account_1411',
                'income_currency_exchange_account_id': 'account_2660',
                'expense_currency_exchange_account_id': 'account_2150',
                'account_journal_early_pay_discount_loss_account_id': 'account_2130',
                'account_journal_early_pay_discount_gain_account_id': 'account_2670',
                'account_sale_tax_id': 'tax_ust_19_skr03',
                'account_purchase_tax_id': 'tax_vst_19_skr03',
                'expense_account_id': 'account_3400',
                'income_account_id': 'account_8400',
                'account_stock_valuation_id': 'account_7200',
            },
        }

    @template('de_skr03', 'account.reconcile.model')
    def _get_de_skr03_reconcile_model(self):
        return {
            'reconcile_3731': {
                'name': 'Discount-EK-7%',
                'line_ids': [
                    Command.create({
                        'account_id': 'account_3731',
                        'amount_type': 'percentage',
                        'tax_ids': [
                            Command.set([
                                'tax_vst_7_skr03',
                            ]),
                        ],
                        'amount_string': '100',
                        'label': 'Discount-EK-7%',
                    }),
                ],
            },
            'reconcile_3736': {
                'name': 'Discount-EK-19%',
                'line_ids': [
                    Command.create({
                        'account_id': 'account_3736',
                        'amount_type': 'percentage',
                        'tax_ids': [
                            Command.set([
                                'tax_vst_19_skr03',
                            ]),
                        ],
                        'amount_string': '100',
                        'label': 'Discount-EK-19%',
                    }),
                ],
            },
            'reconcile_8731': {
                'name': 'Discount-VK-7%',
                'line_ids': [
                    Command.create({
                        'account_id': 'account_8731',
                        'amount_type': 'percentage',
                        'tax_ids': [
                            Command.set([
                                'tax_ust_7_skr03',
                            ]),
                        ],
                        'amount_string': '100',
                        'label': 'Discount-VK-7%',
                    }),
                ],
            },
            'reconcile_8736': {
                'name': 'Discount-VK-19%',
                'line_ids': [
                    Command.create({
                        'account_id': 'account_8736',
                        'amount_type': 'percentage',
                        'tax_ids': [
                            Command.set([
                                'tax_ust_19_skr03',
                            ]),
                        ],
                        'amount_string': '100',
                        'label': 'Discount-VK-19%',
                    }),
                ],
            },
            'reconcile_2401': {
                'name': 'Loss of receivables-7%',
                'line_ids': [
                    Command.create({
                        'account_id': 'account_2401',
                        'amount_type': 'percentage',
                        'tax_ids': [
                            Command.set([
                                'tax_ust_7_skr03',
                            ]),
                        ],
                        'amount_string': '100',
                        'label': 'Loss of receivables-7%',
                    }),
                ],
            },
            'reconcile_2406': {
                'name': 'Loss of receivables-19%',
                'line_ids': [
                    Command.create({
                        'account_id': 'account_2406',
                        'amount_type': 'percentage',
                        'tax_ids': [
                            Command.set([
                                'tax_ust_19_skr03',
                            ]),
                        ],
                        'amount_string': '100',
                        'label': 'Loss of receivables-19%',
                    }),
                ],
            },
        }

    @template('de_skr03', 'account.account')
    def _get_de_skr03_account_account(self):
        return {
            'account_0025': {
                'depreciation_model_id': 'asset_5_year_linear',
                'asset_depreciation_account_id': 'account_0026',
                'asset_expense_account_id': 'account_4822',
            },
            'account_0027': {
                'depreciation_model_id': 'asset_1_year_linear',
                'asset_depreciation_account_id': 'account_0029',
                'asset_expense_account_id': 'account_4822',
            },
            'account_0030': {
                'depreciation_model_id': 'asset_5_year_linear',
                'asset_depreciation_account_id': 'account_0034',
                'asset_expense_account_id': 'account_4822',
            },
            'account_0035': {
                'depreciation_model_id': 'asset_15_year_linear',
                'asset_depreciation_account_id': 'account_0036',
                'asset_expense_account_id': 'account_4822',
            },
            'account_0090': {
                'depreciation_model_id': 'asset_33_year_linear',
                'asset_depreciation_account_id': 'account_0099',
                'asset_expense_account_id': 'account_4831',
            },
            'account_0100': {
                'depreciation_model_id': 'asset_33_year_linear',
                'asset_depreciation_account_id': 'account_0109',
                'asset_expense_account_id': 'account_4831',
            },
            'account_0110': {
                'depreciation_model_id': 'asset_20_year_linear',
                'asset_depreciation_account_id': 'account_0099',
                'asset_expense_account_id': 'account_4831',
            },
            'account_0111': {
                'depreciation_model_id': 'asset_10_year_linear',
                'asset_depreciation_account_id': 'account_0099',
                'asset_expense_account_id': 'account_4831',
            },
            'account_0112': {
                'depreciation_model_id': 'asset_19_year_linear',
                'asset_depreciation_account_id': 'account_0099',
                'asset_expense_account_id': 'account_4831',
            },
            'account_0113': {
                'depreciation_model_id': 'asset_10_year_linear',
                'asset_depreciation_account_id': 'account_0099',
                'asset_expense_account_id': 'account_4831',
            },
            'account_0115': {
                'depreciation_model_id': 'asset_33_year_linear',
                'asset_depreciation_account_id': 'account_0099',
                'asset_expense_account_id': 'account_4831',
            },
            'account_0140': {
                'depreciation_model_id': 'asset_50_year_linear',
                'asset_depreciation_account_id': 'account_0141',
                'asset_expense_account_id': 'account_4831',
            },
            'account_0145': {
                'depreciation_model_id': 'asset_20_year_linear',
                'asset_depreciation_account_id': 'account_0141',
                'asset_expense_account_id': 'account_4831',
            },
            'account_0146': {
                'depreciation_model_id': 'asset_10_year_linear',
                'asset_depreciation_account_id': 'account_0141',
                'asset_expense_account_id': 'account_4831',
            },
            'account_0147': {
                'depreciation_model_id': 'asset_19_year_linear',
                'asset_depreciation_account_id': 'account_0141',
                'asset_expense_account_id': 'account_4831',
            },
            'account_0148': {
                'depreciation_model_id': 'asset_10_year_linear',
                'asset_depreciation_account_id': 'account_0141',
                'asset_expense_account_id': 'account_4831',
            },
            'account_0165': {
                'depreciation_model_id': 'asset_33_year_linear',
                'asset_depreciation_account_id': 'account_0169',
                'asset_expense_account_id': 'account_4831',
            },
            'account_0170': {
                'depreciation_model_id': 'asset_33_year_linear',
                'asset_depreciation_account_id': 'account_0171',
                'asset_expense_account_id': 'account_4831',
            },
            'account_0175': {
                'depreciation_model_id': 'asset_20_year_linear',
                'asset_depreciation_account_id': 'account_0169',
                'asset_expense_account_id': 'account_4831',
            },
            'account_0176': {
                'depreciation_model_id': 'asset_10_year_linear',
                'asset_depreciation_account_id': 'account_0169',
                'asset_expense_account_id': 'account_4831',
            },
            'account_0177': {
                'depreciation_model_id': 'asset_19_year_linear',
                'asset_depreciation_account_id': 'account_0169',
                'asset_expense_account_id': 'account_4831',
            },
            'account_0178': {
                'depreciation_model_id': 'asset_10_year_linear',
                'asset_depreciation_account_id': 'account_0169',
                'asset_expense_account_id': 'account_4831',
            },
            'account_0179': {
                'depreciation_model_id': 'asset_33_year_linear',
                'asset_depreciation_account_id': 'account_0169',
                'asset_expense_account_id': 'account_4831',
            },
            'account_0190': {
                'depreciation_model_id': 'asset_50_year_linear',
                'asset_depreciation_account_id': 'account_0198',
                'asset_expense_account_id': 'account_4831',
            },
            'account_0191': {
                'depreciation_model_id': 'asset_20_year_linear',
                'asset_depreciation_account_id': 'account_0198',
                'asset_expense_account_id': 'account_4831',
            },
            'account_0192': {
                'depreciation_model_id': 'asset_10_year_linear',
                'asset_depreciation_account_id': 'account_0198',
                'asset_expense_account_id': 'account_4831',
            },
            'account_0193': {
                'depreciation_model_id': 'asset_19_year_linear',
                'asset_depreciation_account_id': 'account_0198',
                'asset_expense_account_id': 'account_4831',
            },
            'account_0194': {
                'depreciation_model_id': 'asset_10_year_linear',
                'asset_depreciation_account_id': 'account_0198',
                'asset_expense_account_id': 'account_4831',
            },
            'account_0210': {
                'depreciation_model_id': 'asset_10_year_linear',
                'asset_depreciation_account_id': 'account_0219',
                'asset_expense_account_id': 'account_4830',
            },
            'account_0220': {
                'depreciation_model_id': 'asset_10_year_linear',
                'asset_depreciation_account_id': 'account_0229',
                'asset_expense_account_id': 'account_4830',
            },
            'account_0260': {
                'depreciation_model_id': 'asset_14_year_linear',
                'asset_depreciation_account_id': 'account_0269',
                'asset_expense_account_id': 'account_4830',
            },
            'account_0280': {
                'depreciation_model_id': 'asset_10_year_linear',
                'asset_depreciation_account_id': 'account_0289',
                'asset_expense_account_id': 'account_4830',
            },
            'account_0320': {
                'depreciation_model_id': 'asset_6_year_linear',
                'asset_depreciation_account_id': 'account_0329',
                'asset_expense_account_id': 'account_4832',
            },
            'account_0350': {
                'depreciation_model_id': 'asset_9_year_linear',
                'asset_depreciation_account_id': 'account_0359',
                'asset_expense_account_id': 'account_4832',
            },
            'account_0380': {
                'depreciation_model_id': 'asset_7_year_linear',
                'asset_depreciation_account_id': 'account_0389',
                'asset_expense_account_id': 'account_4832',
            },
            'account_03801': {
                'depreciation_model_id': 'asset_7_year_linear',
                'asset_depreciation_account_id': 'account_0389',
                'asset_expense_account_id': 'account_4832',
            },
            'account_03802': {
                'depreciation_model_id': 'asset_3_year_linear',
                'asset_depreciation_account_id': 'account_0389',
                'asset_expense_account_id': 'account_4832',
            },
            'account_03803': {
                'depreciation_model_id': 'asset_8_year_linear',
                'asset_depreciation_account_id': 'account_0389',
                'asset_expense_account_id': 'account_4830',
            },
            'account_03804': {
                'depreciation_model_id': 'asset_7_year_linear',
                'asset_depreciation_account_id': 'account_0389',
                'asset_expense_account_id': 'account_4830',
            },
            'account_0410': {
                'depreciation_model_id': 'asset_1_year_linear',
                'asset_depreciation_account_id': 'account_0419',
                'asset_expense_account_id': 'account_4830',
            },
            'account_04101': {
                'depreciation_model_id': 'asset_5_year_linear',
                'asset_depreciation_account_id': 'account_0419',
                'asset_expense_account_id': 'account_4830',
            },
            'account_04102': {
                'depreciation_model_id': 'asset_7_year_linear',
                'asset_depreciation_account_id': 'account_0419',
                'asset_expense_account_id': 'account_4830',
            },
            'account_0420': {
                'depreciation_model_id': 'asset_13_year_linear',
                'asset_depreciation_account_id': 'account_0429',
                'asset_expense_account_id': 'account_4830',
            },
            'account_0430': {
                'depreciation_model_id': 'asset_8_year_linear',
                'asset_depreciation_account_id': 'account_0439',
                'asset_expense_account_id': 'account_4830',
            },
            'account_0440': {
                'depreciation_model_id': 'asset_5_year_linear',
                'asset_depreciation_account_id': 'account_0449',
                'asset_expense_account_id': 'account_4830',
            },
            'account_0460': {
                'depreciation_model_id': 'asset_5_year_linear',
                'asset_depreciation_account_id': 'account_0469',
                'asset_expense_account_id': 'account_4830',
            },
            'account_0480': {
                'depreciation_model_id': 'asset_1_year_linear',
                'asset_depreciation_account_id': 'account_0484',
                'asset_expense_account_id': 'account_4830',
            },
            'account_0485': {
                'depreciation_model_id': 'asset_5_year_linear',
                'asset_depreciation_account_id': 'account_0489',
                'asset_expense_account_id': 'account_4830',
            },
            'account_7200': {
                'account_stock_expense_id': 'account_3000',
                'account_stock_variation_id': 'account_3955',
            },
        }
