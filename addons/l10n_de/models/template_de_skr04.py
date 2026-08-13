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
            'property_account_expense_categ_id': 'chart_skr04_5400',
            'property_account_income_categ_id': 'chart_skr04_4400',
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
