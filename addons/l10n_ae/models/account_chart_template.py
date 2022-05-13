# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, Command

class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    def _get_ae_chart_template_data(self, template_code, company):
        res = {
            **self._get_chart_template_data(template_code, company),
            "account.fiscal.position": self._get_ae_fiscal_position(template_code, company),
            "account.fiscal.position.tax": self._get_ae_fiscal_position_tax(template_code, company),
        }
        return res

    def _get_ae_res_company(self, template_code, company):
        company = (company or self.env.company)
        cid = company.id
        return {
            company.get_external_id()[company.id]: {
                'account_fiscal_country_id': 'base.ae',
                'account_default_pos_receivable_account_id': f'account.{cid}_uae_account_102012',
                'income_currency_exchange_account_id': f'account.{cid}_uae_account_500011',
                'expense_currency_exchange_account_id': f'account.{cid}_uae_account_400053',
            }
        }

    def _get_ae_account_journal(self, template_code, company):
        """ If UAE chart, we add 2 new journals TA and IFRS"""
        cid = (company or self.env.company).id
        return {
            **self._get_account_journal(template_code, company),
            f'{cid}_journal_tax_adjustments': {
                "name": "Tax Adjustments",
                "company_id": cid,
                "code": "TA",
                "type": "general",
                "sequence": 1,
                "show_on_dashboard": True,
            },
            f'{cid}_journal_ifrs': {
                "name": "IFRS 16",
                "company_id": cid,
                "code": "IFRS",
                "type": "general",
                "sequence": 10,
                "show_on_dashboard": True,
            }
        }

    def _get_ae_template_data(self, template_code, company):
        cid = (company or self.env.company).id
        return {
            'code_digits': '6',
            'bank_account_code_prefix': '101',
            'cash_account_code_prefix': '105',
            'transfer_account_code_prefix': '100',
            'property_account_receivable_id': f'account.{cid}_uae_account_102011',
            'property_account_payable_id': f'account.{cid}_uae_account_201002',
            'property_tax_receivable_account_id': f'account.{cid}_uae_account_100103',
            'property_tax_payable_account_id': f'account.{cid}_uae_account_202003',
            'property_account_expense_categ_id': f'account.{cid}_uae_account_400001',
            'property_account_income_categ_id': f'account.{cid}_uae_account_500001',
        }

    def _get_ae_account_tax(self, template_code, company):
        cid = (company or self.env.company).id
        return {
            f'{cid}_uae_sale_tax_5_dubai': {
                'name': 'VAT 5% (Dubai)',
                'type_tax_use': 'sale',
                'amount': 5.0,
                'amount_type': 'percent',
                'description': 'VAT 5%',
                'tax_group_id': f'account.{cid}_ae_tax_group_5',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_standard_rated_supplies_base_dubai',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_uae_account_201017',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_standard_rated_supplies_vat_dubai',
                        ],
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_standard_rated_supplies_base_dubai',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_uae_account_201017',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_standard_rated_supplies_vat_dubai',
                        ],
                    }),
                ],
            },
            f'{cid}_uae_sale_tax_5_abu_dhabi': {
                'name': 'VAT 5% (Abu Dhabi)',
                'type_tax_use': 'sale',
                'amount': 5.0,
                'amount_type': 'percent',
                'description': 'VAT 5%',
                'tax_group_id': f'account.{cid}_ae_tax_group_5',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_standard_rated_supplies_base_abu_dhabi',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_uae_account_201017',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_standard_rated_supplies_vat_abu_dhabi',
                        ],
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_standard_rated_supplies_base_abu_dhabi',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_uae_account_201017',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_standard_rated_supplies_vat_abu_dhabi',
                        ],
                    }),
                ],
            },
            f'{cid}_uae_sale_tax_5_sharjah': {
                'name': 'VAT 5% (Sharjah)',
                'type_tax_use': 'sale',
                'amount': 5.0,
                'amount_type': 'percent',
                'description': 'VAT 5%',
                'tax_group_id': f'account.{cid}_ae_tax_group_5',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_standard_rated_supplies_base_sharjah',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_uae_account_201017',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_standard_rated_supplies_vat_sharjah',
                        ],
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_standard_rated_supplies_base_sharjah',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_uae_account_201017',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_standard_rated_supplies_vat_sharjah',
                        ],
                    }),
                ],
            },
            f'{cid}_uae_sale_tax_5_ajman': {
                'name': 'VAT 5% (Ajman)',
                'type_tax_use': 'sale',
                'amount': 5.0,
                'amount_type': 'percent',
                'description': 'VAT 5%',
                'tax_group_id': f'account.{cid}_ae_tax_group_5',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_standard_rated_supplies_base_ajman',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_uae_account_201017',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_standard_rated_supplies_vat_ajman',
                        ],
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_standard_rated_supplies_base_ajman',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_uae_account_201017',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_standard_rated_supplies_vat_ajman',
                        ],
                    }),
                ],
            },
            f'{cid}_uae_sale_tax_5_umm_al_quwain': {
                'name': 'VAT 5% (Umm Al Quwain)',
                'type_tax_use': 'sale',
                'amount': 5.0,
                'amount_type': 'percent',
                'description': 'VAT 5%',
                'tax_group_id': f'account.{cid}_ae_tax_group_5',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_standard_rated_supplies_base_umm_al_quwain',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_uae_account_201017',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_standard_rated_supplies_vat_umm_al_quwain',
                        ],
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_standard_rated_supplies_base_umm_al_quwain',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_uae_account_201017',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_standard_rated_supplies_vat_umm_al_quwain',
                        ],
                    }),
                ],
            },
            f'{cid}_uae_sale_tax_5_ras_al_khaima': {
                'name': 'VAT 5% (Ras Al-Khaima)',
                'type_tax_use': 'sale',
                'amount': 5.0,
                'amount_type': 'percent',
                'description': 'VAT 5%',
                'tax_group_id': f'account.{cid}_ae_tax_group_5',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_standard_rated_supplies_base_ras_al_khaima',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_uae_account_201017',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_standard_rated_supplies_vat_ras_al_khaima',
                        ],
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_standard_rated_supplies_base_ras_al_khaima',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_uae_account_201017',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_standard_rated_supplies_vat_ras_al_khaima',
                        ],
                    }),
                ],
            },
            f'{cid}_uae_sale_tax_5_fujairah': {
                'name': 'VAT 5% (Fujairah)',
                'type_tax_use': 'sale',
                'amount': 5.0,
                'amount_type': 'percent',
                'description': 'VAT 5%',
                'tax_group_id': f'account.{cid}_ae_tax_group_5',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_standard_rated_supplies_base_fujairah',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_uae_account_201017',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_standard_rated_supplies_vat_fujairah',
                        ],
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_standard_rated_supplies_base_fujairah',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_uae_account_201017',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_standard_rated_supplies_vat_fujairah',
                        ],
                    }),
                ],
            },
            f'{cid}_uae_sale_tax_exempted': {
                'name': 'Exempted Tax',
                'type_tax_use': 'sale',
                'amount': 0.0,
                'amount_type': 'percent',
                'description': 'Exempted',
                'tax_group_id': f'account.{cid}_ae_tax_group_exempted',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_exempt_supplies_base',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_exempt_supplies_base',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_uae_sale_tax_0': {
                'name': 'VAT 0%',
                'type_tax_use': 'sale',
                'amount': 0.0,
                'amount_type': 'percent',
                'description': 'VAT 0%',
                'tax_group_id': f'account.{cid}_ae_tax_group_0',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_zero_rated_supplies_base',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_zero_rated_supplies_base',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_uae_export_tax': {
                'name': 'Export Tax 0%',
                'type_tax_use': 'sale',
                'amount': 0.0,
                'amount_type': 'percent',
                'description': 'Export Tax',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_uae_sale_tax_reverse_charge_dubai': {
                'name': 'Reverse Charge Provision (Dubai)',
                'type_tax_use': 'sale',
                'amount': 5.0,
                'amount_type': 'percent',
                'description': 'Supplies subject to reverse charge provisions',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_expense_supplies_reverse_base',
                            f'account.{cid}_tax_report_line_supplies_reverse_charge_base',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_uae_account_104041',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_expense_supplies_reverse_vat',
                        ],
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_uae_account_201017',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_supplies_reverse_charge_vat',
                        ],
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_expense_supplies_reverse_base',
                            f'account.{cid}_tax_report_line_supplies_reverse_charge_base',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_uae_account_104041',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_expense_supplies_reverse_vat',
                        ],
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_uae_account_201017',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_supplies_reverse_charge_vat',
                        ],
                    }),
                ],
            },
            f'{cid}_uae_sale_tax_reverse_charge_abu_dhabi': {
                'name': 'Reverse Charge Provision (Abu Dhabi)',
                'type_tax_use': 'sale',
                'amount': 5.0,
                'amount_type': 'percent',
                'description': 'Supplies subject to reverse charge provisions',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_expense_supplies_reverse_base',
                            f'account.{cid}_tax_report_line_supplies_reverse_charge_base',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_uae_account_104041',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_expense_supplies_reverse_vat',
                        ],
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_uae_account_201017',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_supplies_reverse_charge_vat',
                        ],
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_expense_supplies_reverse_base',
                            f'account.{cid}_tax_report_line_supplies_reverse_charge_base',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_uae_account_104041',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_expense_supplies_reverse_vat',
                        ],
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_uae_account_201017',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_supplies_reverse_charge_vat',
                        ],
                    }),
                ],
            },
            f'{cid}_uae_sale_tax_reverse_charge_sharjah': {
                'name': 'Reverse Charge Provision (Sharjah)',
                'type_tax_use': 'sale',
                'amount': 5.0,
                'amount_type': 'percent',
                'description': 'Supplies subject to reverse charge provisions',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_expense_supplies_reverse_base',
                            f'account.{cid}_tax_report_line_supplies_reverse_charge_base',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_uae_account_104041',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_expense_supplies_reverse_vat',
                        ],
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_uae_account_201017',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_supplies_reverse_charge_vat',
                        ],
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_expense_supplies_reverse_base',
                            f'account.{cid}_tax_report_line_supplies_reverse_charge_base',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_uae_account_104041',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_expense_supplies_reverse_vat',
                        ],
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_uae_account_201017',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_supplies_reverse_charge_vat',
                        ],
                    }),
                ],
            },
            f'{cid}_uae_sale_tax_reverse_charge_ajman': {
                'name': 'Reverse Charge Provision (Ajman)',
                'type_tax_use': 'sale',
                'amount': 5.0,
                'amount_type': 'percent',
                'description': 'Supplies subject to reverse charge provisions',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_expense_supplies_reverse_base',
                            f'account.{cid}_tax_report_line_supplies_reverse_charge_base',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_uae_account_104041',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_expense_supplies_reverse_vat',
                        ],
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_uae_account_201017',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_supplies_reverse_charge_vat',
                        ],
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_expense_supplies_reverse_base',
                            f'account.{cid}_tax_report_line_supplies_reverse_charge_base',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_uae_account_104041',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_expense_supplies_reverse_vat',
                        ],
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_uae_account_201017',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_supplies_reverse_charge_vat',
                        ],
                    }),
                ],
            },
            f'{cid}_uae_sale_tax_reverse_charge_umm_al_quwain': {
                'name': 'Reverse Charge Provision (Umm Al Quwain)',
                'type_tax_use': 'sale',
                'amount': 5.0,
                'amount_type': 'percent',
                'description': 'Supplies subject to reverse charge provisions',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_expense_supplies_reverse_base',
                            f'account.{cid}_tax_report_line_supplies_reverse_charge_base',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_uae_account_104041',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_expense_supplies_reverse_vat',
                        ],
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_uae_account_201017',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_supplies_reverse_charge_vat',
                        ],
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_expense_supplies_reverse_base',
                            f'account.{cid}_tax_report_line_supplies_reverse_charge_base',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_uae_account_104041',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_expense_supplies_reverse_vat',
                        ],
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_uae_account_201017',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_supplies_reverse_charge_vat',
                        ],
                    }),
                ],
            },
            f'{cid}_uae_sale_tax_reverse_charge_ras_al_khaima': {
                'name': 'Reverse Charge Provision (Ras Al-Khaima)',
                'type_tax_use': 'sale',
                'amount': 5.0,
                'amount_type': 'percent',
                'description': 'Supplies subject to reverse charge provisions',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_expense_supplies_reverse_base',
                            f'account.{cid}_tax_report_line_supplies_reverse_charge_base',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_uae_account_104041',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_expense_supplies_reverse_vat',
                        ],
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_uae_account_201017',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_supplies_reverse_charge_vat',
                        ],
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_expense_supplies_reverse_base',
                            f'account.{cid}_tax_report_line_supplies_reverse_charge_base',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_uae_account_104041',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_expense_supplies_reverse_vat',
                        ],
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_uae_account_201017',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_supplies_reverse_charge_vat',
                        ],
                    }),
                ],
            },
            f'{cid}_uae_sale_tax_reverse_charge_fujairah': {
                'name': 'Reverse Charge Provision (Fujairah)',
                'type_tax_use': 'sale',
                'amount': 5.0,
                'amount_type': 'percent',
                'description': 'Supplies subject to reverse charge provisions',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_expense_supplies_reverse_base',
                            f'account.{cid}_tax_report_line_supplies_reverse_charge_base',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_uae_account_104041',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_expense_supplies_reverse_vat',
                        ],
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_uae_account_201017',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_supplies_reverse_charge_vat',
                        ],
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_expense_supplies_reverse_base',
                            f'account.{cid}_tax_report_line_supplies_reverse_charge_base',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_uae_account_104041',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_expense_supplies_reverse_vat',
                        ],
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_uae_account_201017',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_supplies_reverse_charge_vat',
                        ],
                    }),
                ],
            },
            f'{cid}_uae_sale_tax_tourist_refund': {
                'name': 'Tourist Refund scheme 5%',
                'type_tax_use': 'sale',
                'amount': 5.0,
                'amount_type': 'percent',
                'description': 'Tax Refunds provided to Tourists under the Tax Refunds for Tourists Scheme',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_tax_refund_tourist_base',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_uae_account_201017',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_tax_refund_tourist_vat',
                        ],
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_tax_refund_tourist_base',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_uae_account_201017',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_tax_refund_tourist_vat',
                        ],
                    }),
                ],
            },
            f'{cid}_uae_purchase_tax_5': {
                'name': 'VAT 5%',
                'type_tax_use': 'purchase',
                'amount': 5.0,
                'amount_type': 'percent',
                'description': 'VAT 5%',
                'tax_group_id': f'account.{cid}_ae_tax_group_5',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_standard_rated_expense_base',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_uae_account_104041',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_standard_rated_expense_vat',
                        ],
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_standard_rated_expense_base',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_uae_account_104041',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_standard_rated_expense_vat',
                        ],
                    }),
                ],
            },
            f'{cid}_uae_purchase_tax_exempted': {
                'name': 'Exempted Tax',
                'type_tax_use': 'purchase',
                'amount': 0.0,
                'amount_type': 'percent',
                'description': 'Exempted Tax',
                'tax_group_id': f'account.{cid}_ae_tax_group_exempted',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_uae_purchase_tax_0': {
                'name': 'VAT 0%',
                'type_tax_use': 'purchase',
                'amount': 0.0,
                'amount_type': 'percent',
                'description': 'VAT 0%',
                'tax_group_id': f'account.{cid}_ae_tax_group_0',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_uae_import_tax': {
                'name': 'Import Tax 5%',
                'type_tax_use': 'purchase',
                'amount': 5.0,
                'amount_type': 'percent',
                'description': 'Import Tax',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_import_uae_base',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_uae_account_104041',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_import_uae_vat',
                        ],
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_import_uae_base',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_uae_account_104041',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_import_uae_vat',
                        ],
                    }),
                ],
            },
            f'{cid}_uae_purchase_tax_reverse_charge': {
                'name': 'Reverse Charge Provision',
                'type_tax_use': 'purchase',
                'amount': 5.0,
                'amount_type': 'percent',
                'description': 'Supplies subject to reverse charge provisions',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_expense_supplies_reverse_base',
                            f'account.{cid}_tax_report_line_supplies_reverse_charge_base',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_uae_account_104041',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_expense_supplies_reverse_vat',
                        ],
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_uae_account_201017',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_supplies_reverse_charge_vat',
                        ],
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_expense_supplies_reverse_base',
                            f'account.{cid}_tax_report_line_supplies_reverse_charge_base',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_uae_account_104041',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_expense_supplies_reverse_vat',
                        ],
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_uae_account_201017',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_supplies_reverse_charge_vat',
                        ],
                    }),
                ],
            }
        }

    def _get_ae_fiscal_position(self, template_code, company):
        cid = (company or self.env.company).id
        return {
            f'{cid}_account_fiscal_position_dubai': {
                'name': 'Dubai',
                'auto_apply': 1,
                'sequence': 16,
                'country_id': 'base.ae',
                'state_ids': [
                    Command.set([
                        'base.state_ae_du',
                    ]),
                ],
            },
            f'{cid}_account_fiscal_position_abu_dhabi': {
                'name': 'Abu Dhabi',
                'auto_apply': 1,
                'sequence': 16,
                'country_id': 'base.ae',
                'state_ids': [
                    Command.set([
                        'base.state_ae_az',
                    ]),
                ],
            },
            f'{cid}_account_fiscal_position_sharjah': {
                'name': 'Sharjah',
                'auto_apply': 1,
                'sequence': 16,
                'country_id': 'base.ae',
                'state_ids': [
                    Command.set([
                        'base.state_ae_sh',
                    ]),
                ],
            },
            f'{cid}_account_fiscal_position_ajman': {
                'name': 'Ajman',
                'auto_apply': 1,
                'sequence': 16,
                'country_id': 'base.ae',
                'state_ids': [
                    Command.set([
                        'base.state_ae_aj',
                    ]),
                ],
            },
            f'{cid}_account_fiscal_position_umm_al_quwain': {
                'name': 'Umm Al Quwain',
                'auto_apply': 1,
                'sequence': 16,
                'country_id': 'base.ae',
                'state_ids': [
                    Command.set([
                        'base.state_ae_uq',
                    ]),
                ],
            },
            f'{cid}_account_fiscal_position_ras_al_khaima': {
                'name': 'Ras Al-Khaima',
                'auto_apply': 1,
                'sequence': 16,
                'country_id': 'base.ae',
                'state_ids': [
                    Command.set([
                        'base.state_ae_rk',
                    ]),
                ],
            },
            f'{cid}_account_fiscal_position_fujairah': {
                'name': 'Fujairah',
                'auto_apply': 1,
                'sequence': 16,
                'country_id': 'base.ae',
                'state_ids': [
                    Command.set([
                        'base.state_ae_fu',
                    ]),
                ],
            },
            f'{cid}_account_fiscal_position_non_uae_countries': {
                'name': 'Non-UAE',
                'sequence': 20,
                'auto_apply': 1,
            }
        }

    def _get_ae_fiscal_position_tax(self, template_code, company):
        cid = (company or self.env.company).id
        return {
            f'{cid}_account_fiscal_position_abu_dhabi_01': {
                'tax_src_id': f'account.{cid}_uae_sale_tax_5_dubai',
                'tax_dest_id': f'account.{cid}_uae_sale_tax_5_abu_dhabi',
                'position_id': f'account.{cid}_account_fiscal_position_abu_dhabi',
            },
            f'{cid}_account_fiscal_position_sharjah_01': {
                'tax_src_id': f'account.{cid}_uae_sale_tax_5_dubai',
                'tax_dest_id': f'account.{cid}_uae_sale_tax_5_sharjah',
                'position_id': f'account.{cid}_account_fiscal_position_sharjah',
            },
            f'{cid}_account_fiscal_position_ajman_01': {
                'tax_src_id': f'account.{cid}_uae_sale_tax_5_dubai',
                'tax_dest_id': f'account.{cid}_uae_sale_tax_5_ajman',
                'position_id': f'account.{cid}_account_fiscal_position_ajman',
            },
            f'{cid}_account_fiscal_position_umm_al_quwain_01': {
                'tax_src_id': f'account.{cid}_uae_sale_tax_5_dubai',
                'tax_dest_id': f'account.{cid}_uae_sale_tax_5_umm_al_quwain',
                'position_id': f'account.{cid}_account_fiscal_position_umm_al_quwain',
            },
            f'{cid}_account_fiscal_position_ras_al_khaima_01': {
                'tax_src_id': f'account.{cid}_uae_sale_tax_5_dubai',
                'tax_dest_id': f'account.{cid}_uae_sale_tax_5_ras_al_khaima',
                'position_id': f'account.{cid}_account_fiscal_position_ras_al_khaima',
            },
            f'{cid}_account_fiscal_position_fujairah_01': {
                'tax_src_id': f'account.{cid}_uae_sale_tax_5_dubai',
                'tax_dest_id': f'account.{cid}_uae_sale_tax_5_fujairah',
                'position_id': f'account.{cid}_account_fiscal_position_fujairah',
            },
            f'{cid}_acccount_fiscal_position_tax_non_uae_01': {
                'tax_src_id': f'account.{cid}_uae_sale_tax_5_dubai',
                'tax_dest_id': f'account.{cid}_uae_sale_tax_0',
                'position_id': f'account.{cid}_account_fiscal_position_non_uae_countries',
            },
            f'{cid}_acccount_fiscal_position_tax_non_uae_02': {
                'tax_src_id': f'account.{cid}_uae_purchase_tax_5',
                'tax_dest_id': f'account.{cid}_uae_purchase_tax_reverse_charge',
                'position_id': f'account.{cid}_account_fiscal_position_non_uae_countries',
            }
        }
