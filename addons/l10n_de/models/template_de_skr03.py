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
            'property_account_expense_categ_id': 'account_3400',
            'property_account_income_categ_id': 'account_8400',
            'property_stock_account_input_categ_id': 'account_3970',
            'property_stock_account_output_categ_id': 'account_3980',
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
