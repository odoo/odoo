# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, Command


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    def _get_se_chart_template_data(self, template_code, company):
        return {
            **self._get_chart_template_data(template_code, company),
            'account.fiscal.position': self._get_se_fiscal_position(template_code, company),
            'account.fiscal.position.tax': self._get_se_fiscal_position_tax(template_code, company),
            'account.fiscal.position.account': self._get_se_fiscal_position_account(template_code, company),
        }

    def _get_se_k2_account_account(self, template_code, company):
        accounts = self._get_account_account('se', company)
        accounts.update(self._load_csv(template_code, company, 'account.account-k2.csv', model='account.account'))
        return accounts

    def _get_se_k3_account_account(self, template_code, company):
        accounts = self._get_se_k2_account_account('se_k2', company)
        accounts.update(self._load_csv(template_code, company, 'account.account-k3.csv', model='account.account'))
        return accounts

    def _get_se_template_data(self, template_code, company):
        cid = (company or self.env.company).id
        return {
            'code_digits': '4',
            'bank_account_code_prefix': '193',
            'cash_account_code_prefix': '191',
            'transfer_account_code_prefix': '194',
            'property_account_receivable_id': f'account.{cid}_a1510',
            'property_account_payable_id': f'account.{cid}_a2440',
            'property_account_expense_categ_id': f'account.{cid}_a4000',
            'property_account_income_categ_id': f'account.{cid}_a3001',
            'property_stock_account_input_categ_id': f'account.{cid}_a4960',
            'property_stock_account_output_categ_id': f'account.{cid}_a4960',
            'property_stock_valuation_account_id': f'account.{cid}_a1410',
        }

    def _get_se_account_tax_group(self, template_code, company):
        cid = (company or self.env.company).id
        country_id = self.env.ref('base.se').id
        return {
            f'{cid}_tax_group_25': {
                'name': 'VAT 25%',
                'country_id': country_id,
                'property_tax_payable_account_id': f'account.{cid}_a2610',
                'property_tax_receivable_account_id': f'account.{cid}_a2640',
            }, f'{cid}_tax_group_12': {
                'name': 'VAT 12%',
                'country_id': country_id,
                'property_tax_payable_account_id': f'account.{cid}_a2620',
                'property_tax_receivable_account_id': f'account.{cid}_a2640',
            }, f'{cid}_tax_group_6': {
                'name': 'VAT 6%',
                'country_id': country_id,
                'property_tax_payable_account_id': f'account.{cid}_a2630',
                'property_tax_receivable_account_id': f'account.{cid}_a2640',
            }, f'{cid}_tax_group_0': {
                'name': 'VAT 0%',
                'country_id': country_id
            }
        }

    def _get_se_account_tax(self, template_code, company):
        cid = (company or self.env.company).id
        tags = self._get_tag_mapper(template_code)
        return {
            f'{cid}_sale_tax_25_goods': {
                'name': 'Utgående moms 25%',
                'description': 'ST25',
                'amount': 25.0,
                'type_tax_use': 'sale',
                'tax_group_id': f'account.{cid}_tax_group_25',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+se_05'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a2611',
                        'tag_ids': tags('+se_10'),
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('-se_05'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a2611',
                        'tag_ids': tags('-se_10'),
                    }),
                ],
            },
            f'{cid}_sale_tax_25_services': {
                'name': 'Utgående moms Tjänst 25%',
                'description': 'ST25',
                'amount': 25.0,
                'type_tax_use': 'sale',
                'tax_group_id': f'account.{cid}_tax_group_25',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+se_05'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a2611',
                        'tag_ids': tags('+se_10'),
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('-se_05'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a2611',
                        'tag_ids': tags('-se_10'),
                    }),
                ],
            },
            f'{cid}_purchase_tax_25_goods': {
                'name': 'Ingående moms 25%',
                'description': 'PT25',
                'amount': 25.0,
                'type_tax_use': 'purchase',
                'tax_group_id': f'account.{cid}_tax_group_25',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a2641',
                        'tag_ids': tags('-se_48'),
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
                        'account_id': f'account.{cid}_a2641',
                        'tag_ids': tags('+se_48'),
                    }),
                ],
            },
            f'{cid}_purchase_tax_25_services': {
                'name': 'Ingående moms Tjänst 25%',
                'description': 'PT25',
                'amount': 25.0,
                'type_tax_use': 'purchase',
                'tax_group_id': f'account.{cid}_tax_group_25',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a2641',
                        'tag_ids': tags('-se_48'),
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
                        'account_id': f'account.{cid}_a2641',
                        'tag_ids': tags('+se_48'),
                    }),
                ],
            },
            f'{cid}_sale_tax_12_goods': {
                'name': 'Utgående moms 12%',
                'description': 'ST12',
                'amount': 12.0,
                'type_tax_use': 'sale',
                'tax_group_id': f'account.{cid}_tax_group_12',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+se_05'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a2621',
                        'tag_ids': tags('+se_11'),
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('-se_05'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a2621',
                        'tag_ids': tags('-se_11'),
                    }),
                ],
            },
            f'{cid}_sale_tax_12_services': {
                'name': 'Utgående moms Tjänst 12%',
                'description': 'ST12',
                'amount': 12.0,
                'type_tax_use': 'sale',
                'tax_group_id': f'account.{cid}_tax_group_12',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+se_05'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a2621',
                        'tag_ids': tags('+se_11'),
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('-se_05'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a2621',
                        'tag_ids': tags('-se_11'),
                    }),
                ],
            },
            f'{cid}_purchase_tax_12_goods': {
                'name': 'Ingående moms 12%',
                'description': 'PT12',
                'amount': 12.0,
                'type_tax_use': 'purchase',
                'tax_group_id': f'account.{cid}_tax_group_12',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a2641',
                        'tag_ids': tags('-se_48'),
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
                        'account_id': f'account.{cid}_a2641',
                        'tag_ids': tags('+se_48'),
                    }),
                ],
            },
            f'{cid}_purchase_tax_12_services': {
                'name': 'Ingående moms Tjänst 12%',
                'description': 'PT12',
                'amount': 12.0,
                'type_tax_use': 'purchase',
                'tax_group_id': f'account.{cid}_tax_group_12',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a2641',
                        'tag_ids': tags('-se_48'),
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
                        'account_id': f'account.{cid}_a2641',
                        'tag_ids': tags('+se_48'),
                    }),
                ],
            },
            f'{cid}_sale_tax_6_goods': {
                'name': 'Utgående moms 6%',
                'description': 'ST6',
                'amount': 6.0,
                'type_tax_use': 'sale',
                'tax_group_id': f'account.{cid}_tax_group_6',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+se_05'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a2631',
                        'tag_ids': tags('+se_12'),
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('-se_05'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a2631',
                        'tag_ids': tags('-se_12'),
                    }),
                ],
            },
            f'{cid}_sale_tax_6_services': {
                'name': 'Utgående moms Tjänst 6%',
                'description': 'ST6',
                'amount': 6.0,
                'type_tax_use': 'sale',
                'tax_group_id': f'account.{cid}_tax_group_6',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+se_05'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a2631',
                        'tag_ids': tags('+se_12'),
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('-se_05'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a2631',
                        'tag_ids': tags('-se_12'),
                    }),
                ],
            },
            f'{cid}_purchase_tax_6_goods': {
                'name': 'Ingående moms 6%',
                'description': 'PT6',
                'amount': 6.0,
                'type_tax_use': 'purchase',
                'tax_group_id': f'account.{cid}_tax_group_6',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a2641',
                        'tag_ids': tags('-se_48'),
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
                        'account_id': f'account.{cid}_a2641',
                        'tag_ids': tags('+se_48'),
                    }),
                ],
            },
            f'{cid}_purchase_tax_6_services': {
                'name': 'Ingående moms Tjänst 6%',
                'description': 'PT6',
                'amount': 6.0,
                'type_tax_use': 'purchase',
                'tax_group_id': f'account.{cid}_tax_group_6',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a2641',
                        'tag_ids': tags('-se_48'),
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
                        'account_id': f'account.{cid}_a2641',
                        'tag_ids': tags('+se_48'),
                    }),
                ],
            },
            f'{cid}_sale_tax_services_EC': {
                'name': 'Momsfri försäljning av tjänst EU',
                'description': 'SE0',
                'amount': 0.0,
                'type_tax_use': 'sale',
                'tax_group_id': f'account.{cid}_tax_group_0',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+se_39'),
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
                        'tag_ids': tags('-se_39'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_sale_tax_goods_EC': {
                'name': 'Momsfri Försäljning av varor EU',
                'description': 'SE0',
                'amount': 0.0,
                'type_tax_use': 'sale',
                'tax_group_id': f'account.{cid}_tax_group_0',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+se_35'),
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
                        'tag_ids': tags('-se_35'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_purchase_goods_tax_25_EC': {
                'name': 'Inköp av varor EU moms 25%',
                'description': 'PE25',
                'amount': 25.0,
                'type_tax_use': 'purchase',
                'tax_group_id': f'account.{cid}_tax_group_25',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+se_20'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a2645',
                        'tag_ids': tags('+se_30', '-se_48')
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a2614',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('-se_20'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a2645',
                        'tag_ids': tags('-se_30', '+se_48')
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a2614',
                    }),
                ],
            },
            f'{cid}_purchase_goods_tax_12_EC': {
                'name': 'Inköp av varor EU moms 12%',
                'description': 'PE12',
                'amount': 12.0,
                'type_tax_use': 'purchase',
                'tax_group_id': f'account.{cid}_tax_group_12',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+se_20'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a2645',
                        'tag_ids': tags('+se_31', '-se_48')
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a2624',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('-se_20'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a2645',
                        'tag_ids': tags('-se_31', '+se_48')
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a2624',
                    }),
                ],
            },
            f'{cid}_purchase_goods_tax_6_EC': {
                'name': 'Inköp av varor EU moms 6%',
                'description': 'PE6',
                'amount': 6.0,
                'type_tax_use': 'purchase',
                'tax_group_id': f'account.{cid}_tax_group_6',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+se_20'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a2645',
                        'tag_ids': tags('+se_32', '-se_48')
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a2634',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('-se_20'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a2645',
                        'tag_ids': tags('-se_32', '+se_48')
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a2634',
                    }),
                ],
            },
            f'{cid}_purchase_services_tax_25_EC': {
                'name': 'Inköp av tjänst EU moms 25%',
                'description': 'PE25',
                'amount': 25.0,
                'type_tax_use': 'purchase',
                'tax_group_id': f'account.{cid}_tax_group_25',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+se_21'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a2645',
                        'tag_ids': tags('+se_30', '-se_48')
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a2614',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('-se_21'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a2645',
                        'tag_ids': tags('-se_30', '+se_48')
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a2614',
                    }),
                ],
            },
            f'{cid}_purchase_services_tax_12_EC': {
                'name': 'Inköp av tjänst EU moms 12%',
                'description': 'PE12',
                'amount': 12.0,
                'type_tax_use': 'purchase',
                'tax_group_id': f'account.{cid}_tax_group_12',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+se_21'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a2645',
                        'tag_ids': tags('+se_31', '-se_48')
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a2624',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('-se_21'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a2645',
                        'tag_ids': tags('-se_31', '+se_48')
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a2624',
                    }),
                ],
            },
            f'{cid}_purchase_services_tax_6_EC': {
                'name': 'Inköp av tjänst EU moms 6%',
                'description': 'PE6',
                'amount': 6.0,
                'type_tax_use': 'purchase',
                'tax_group_id': f'account.{cid}_tax_group_6',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+se_21'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a2645',
                        'tag_ids': tags('+se_32', '-se_48')
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a2634',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('-se_21'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a2645',
                        'tag_ids': tags('-se_32', '+se_48')
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a2634',
                    }),
                ],
            },
            f'{cid}_purchase_construction_services_tax_25_EC': {
                'name': 'Inköpta tjänster i Sverige, omvändskattskyldighet, 25 %',
                'description': 'PCS25',
                'amount': 25.0,
                'type_tax_use': 'purchase',
                'tax_group_id': f'account.{cid}_tax_group_25',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+se_24'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a2647',
                        'tag_ids': tags('+se_30', '-se_48')
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a2614',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('-se_24'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a2647',
                        'tag_ids': tags('-se_30', '+se_48')
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a2614',
                    }),
                ],
            },
            f'{cid}_purchase_construction_services_tax_12_EC': {
                'name': 'Inköpta tjänster i Sverige, omvändskattskyldighet, 12 %',
                'description': 'PCS12',
                'amount': 12.0,
                'type_tax_use': 'purchase',
                'tax_group_id': f'account.{cid}_tax_group_12',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+se_24'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a4426',
                        'tag_ids': tags('+se_31', '-se_48')
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a2624',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('-se_24'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a4426',
                        'tag_ids': tags('-se_31', '+se_48')
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a2624',
                    }),
                ],
            },
            f'{cid}_purchase_construction_services_tax_6_EC': {
                'name': 'Inköpta tjänster i Sverige, omvändskattskyldighet, 6 %',
                'description': 'PCS6',
                'amount': 6.0,
                'type_tax_use': 'purchase',
                'tax_group_id': f'account.{cid}_tax_group_6',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+se_24'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a4427',
                        'tag_ids': tags('+se_32', '-se_48')
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a2634',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('-se_24'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a4427',
                        'tag_ids': tags('-se_32', '+se_48')
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a2634',
                    }),
                ],
            },
            f'{cid}_sale_tax_services_NEC': {
                'name': 'Momsfri försäljning av tjänst utanför EU',
                'description': 'SE0',
                'amount': 0.0,
                'type_tax_use': 'sale',
                'tax_group_id': f'account.{cid}_tax_group_0',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+se_39'),
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
                        'tag_ids': tags('-se_39'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_sale_tax_goods_NEC': {
                'name': 'Momsfri försäljning av varor utanför EU',
                'description': 'SE0',
                'amount': 0.0,
                'type_tax_use': 'sale',
                'tax_group_id': f'account.{cid}_tax_group_0',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+se_36'),
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
                        'tag_ids': tags('-se_36'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_purchase_goods_tax_25_NEC': {
                'name': 'Beskattningsunderlag vid import 25%',
                'description': 'PN25',
                'amount': 25.0,
                'type_tax_use': 'purchase',
                'tax_group_id': f'account.{cid}_tax_group_25',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+se_50'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a2645',
                        'tag_ids': tags('+se_60'),
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a2615',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('-se_50'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a2645',
                        'tag_ids': tags('-se_60'),
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a2615',
                    }),
                ],
            },
            f'{cid}_purchase_goods_tax_12_NEC': {
                'name': 'Beskattningsunderlag vid import 12%',
                'description': 'PN12',
                'amount': 12.0,
                'type_tax_use': 'purchase',
                'tax_group_id': f'account.{cid}_tax_group_12',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+se_50'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a2645',
                        'tag_ids': tags('+se_61'),
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a2625',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('-se_50'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a2645',
                        'tag_ids': tags('-se_61'),
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a2625',
                    }),
                ],
            },
            f'{cid}_purchase_goods_tax_6_NEC': {
                'name': 'Beskattningsunderlag vid import 6%',
                'description': 'PN6',
                'amount': 6.0,
                'type_tax_use': 'purchase',
                'tax_group_id': f'account.{cid}_tax_group_6',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+se_50'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a2645',
                        'tag_ids': tags('+se_62'),
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a2635',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('-se_50'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a2645',
                        'tag_ids': tags('-se_62'),
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a2635',
                    }),
                ],
            },
            f'{cid}_purchase_services_tax_25_NEC': {
                'name': 'Inköp av tjänster utanför EU 25%',
                'description': 'PN25',
                'amount': 25.0,
                'type_tax_use': 'purchase',
                'tax_group_id': f'account.{cid}_tax_group_25',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+se_22'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a2645',
                        'tag_ids': tags('+se_30', '-se_48')
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a2614',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('-se_22'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a2645',
                        'tag_ids': tags('-se_30', '+se_48')
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a2614',
                    }),
                ],
            },
            f'{cid}_purchase_services_tax_12_NEC': {
                'name': 'Inköp av tjänster utanför EU 12%',
                'description': 'PN12',
                'amount': 12.0,
                'type_tax_use': 'purchase',
                'tax_group_id': f'account.{cid}_tax_group_12',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+se_22'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a2645',
                        'tag_ids': tags('+se_31', '-se_48')
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a2624',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('-se_22'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a2645',
                        'tag_ids': tags('-se_31', '+se_48')
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a2624',
                    }),
                ],
            },
            f'{cid}_purchase_services_tax_6_NEC': {
                'name': 'Inköp av tjänster utanför EU 6%',
                'description': 'PN6',
                'amount': 6.0,
                'type_tax_use': 'purchase',
                'tax_group_id': f'account.{cid}_tax_group_6',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+se_22'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a2645',
                        'tag_ids': tags('+se_32', '-se_48')
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a2634',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('-se_22'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a2645',
                        'tag_ids': tags('-se_32', '+se_48')
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a2634',
                    }),
                ],
            },
            f'{cid}_triangular_tax_25_goods': {
                'name': 'Trepartshandel - moms 25%',
                'description': 'T25',
                'amount': 25.0,
                'type_tax_use': 'sale',
                'tax_group_id': f'account.{cid}_tax_group_25',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+se_37', '-se_38')
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a2615',
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a2645',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('-se_37', '+se_38')
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a2615',
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a2645',
                    }),
                ],
            },
            f'{cid}_triangular_tax_12_goods': {
                'name': 'Trepartshandel - moms 12%',
                'description': 'T12',
                'amount': 12.0,
                'type_tax_use': 'sale',
                'tax_group_id': f'account.{cid}_tax_group_25',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+se_37', '-se_38')
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a2625',
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a2645',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('-se_37', '+se_38')
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a2625',
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a2645',
                    }),
                ],
            },
            f'{cid}_triangular_tax_6_goods': {
                'name': 'Trepartshandel - moms 6%',
                'description': 'T6',
                'amount': 6.0,
                'type_tax_use': 'sale',
                'tax_group_id': f'account.{cid}_tax_group_25',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+se_37', '-se_38')
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a2635',
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a2645',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('-se_37', '+se_38')
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a2635',
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a2645',
                    }),
                ],
            },
            f'{cid}_triangular_tax_0_goods': {
                'name': 'Trepartshandel - momsfrei',
                'description': 'T0',
                'amount': 0.0,
                'type_tax_use': 'sale',
                'tax_group_id': f'account.{cid}_tax_group_25',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+se_37', '-se_38')
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
                        'tag_ids': tags('-se_37', '+se_38'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            }
        }

    def _get_se_res_company(self, template_code, company):
        company = (company or self.env.company)
        cid = (company or self.env.company).id
        return {
            company.get_external_id()[cid]: {
                'account_fiscal_country_id': 'base.se',
                'account_default_pos_receivable_account_id': f'account.{cid}_a1910',
                'income_currency_exchange_account_id': f'account.{cid}_a3960',
                'expense_currency_exchange_account_id': f'account.{cid}_a3960',
            }
        }

    def _get_se_fiscal_position(self, template_code, company):
        cid = (company or self.env.company).id
        return {
            f'{cid}_fp_sweden': {
                'name': 'Sverige',
                'auto_apply': 1,
                'country_id': 'base.se',
                'vat_required': 1,
                'sequence': 10,
            },
            f'{cid}_fp_euro_b2c': {
                'name': 'Europaunionen (B2C)',
                'auto_apply': 1,
                'country_group_id': 'base.europe',
                'sequence': 11,
            },
            f'{cid}_fp_euro_b2b': {
                'name': 'Europaunionen (B2B)',
                'auto_apply': 1,
                'vat_required': 1,
                'country_group_id': 'base.europe',
                'sequence': 12,
            },
            f'{cid}_fp_outside_euro': {
                'name': 'Utanför Europaunionen',
                'auto_apply': 1,
                'sequence': 13,
            }
        }

    def _get_se_fiscal_position_tax(self, template_code, company):
        cid = (company or self.env.company).id
        return {
            f'{cid}_fpp_euro_25_services': {
                'position_id': f'account.{cid}_fp_euro_b2b',
                'tax_src_id': f'account.{cid}_purchase_tax_25_services',
                'tax_dest_id': f'account.{cid}_purchase_services_tax_25_EC',
            },
            f'{cid}_fpp_euro_25_goods': {
                'position_id': f'account.{cid}_fp_euro_b2b',
                'tax_src_id': f'account.{cid}_purchase_tax_25_goods',
                'tax_dest_id': f'account.{cid}_purchase_goods_tax_25_EC',
            },
            f'{cid}_fpp_euro_12_services': {
                'position_id': f'account.{cid}_fp_euro_b2b',
                'tax_src_id': f'account.{cid}_purchase_tax_12_services',
                'tax_dest_id': f'account.{cid}_purchase_services_tax_12_EC',
            },
            f'{cid}_fpp_euro_12_goods': {
                'position_id': f'account.{cid}_fp_euro_b2b',
                'tax_src_id': f'account.{cid}_purchase_tax_12_goods',
                'tax_dest_id': f'account.{cid}_purchase_goods_tax_12_EC',
            },
            f'{cid}_fpp_euro_6_services': {
                'position_id': f'account.{cid}_fp_euro_b2b',
                'tax_src_id': f'account.{cid}_purchase_tax_6_services',
                'tax_dest_id': f'account.{cid}_purchase_services_tax_6_EC',
            },
            f'{cid}_fpp_euro_6_goods': {
                'position_id': f'account.{cid}_fp_euro_b2b',
                'tax_src_id': f'account.{cid}_purchase_tax_6_goods',
                'tax_dest_id': f'account.{cid}_purchase_goods_tax_6_EC',
            },
            f'{cid}_fps_euro_25_services': {
                'position_id': f'account.{cid}_fp_euro_b2b',
                'tax_src_id': f'account.{cid}_sale_tax_25_services',
                'tax_dest_id': f'account.{cid}_sale_tax_services_EC',
            },
            f'{cid}_fps_euro_25_goods': {
                'position_id': f'account.{cid}_fp_euro_b2b',
                'tax_src_id': f'account.{cid}_sale_tax_25_goods',
                'tax_dest_id': f'account.{cid}_sale_tax_goods_EC',
            },
            f'{cid}_fps_euro_12_services': {
                'position_id': f'account.{cid}_fp_euro_b2b',
                'tax_src_id': f'account.{cid}_sale_tax_12_services',
                'tax_dest_id': f'account.{cid}_sale_tax_services_EC',
            },
            f'{cid}_fps_euro_12_goods': {
                'position_id': f'account.{cid}_fp_euro_b2b',
                'tax_src_id': f'account.{cid}_sale_tax_12_goods',
                'tax_dest_id': f'account.{cid}_sale_tax_goods_EC',
            },
            f'{cid}_fps_euro_6_services': {
                'position_id': f'account.{cid}_fp_euro_b2b',
                'tax_src_id': f'account.{cid}_sale_tax_6_services',
                'tax_dest_id': f'account.{cid}_sale_tax_services_EC',
            },
            f'{cid}_fps_euro_6_goods': {
                'position_id': f'account.{cid}_fp_euro_b2b',
                'tax_src_id': f'account.{cid}_sale_tax_6_goods',
                'tax_dest_id': f'account.{cid}_sale_tax_goods_EC',
            },
            f'{cid}_fpp_outside_25_services': {
                'position_id': f'account.{cid}_fp_outside_euro',
                'tax_src_id': f'account.{cid}_purchase_tax_25_services',
                'tax_dest_id': f'account.{cid}_purchase_services_tax_25_NEC',
            },
            f'{cid}_fpp_outside_25_goods': {
                'position_id': f'account.{cid}_fp_outside_euro',
                'tax_src_id': f'account.{cid}_purchase_tax_25_goods',
                'tax_dest_id': f'account.{cid}_purchase_goods_tax_25_NEC',
            },
            f'{cid}_fpp_outside_12_services': {
                'position_id': f'account.{cid}_fp_outside_euro',
                'tax_src_id': f'account.{cid}_purchase_tax_12_services',
                'tax_dest_id': f'account.{cid}_purchase_services_tax_12_NEC',
            },
            f'{cid}_fpp_outside_12_goods': {
                'position_id': f'account.{cid}_fp_outside_euro',
                'tax_src_id': f'account.{cid}_purchase_tax_12_goods',
                'tax_dest_id': f'account.{cid}_purchase_goods_tax_12_NEC',
            },
            f'{cid}_fpp_outside_6_services': {
                'position_id': f'account.{cid}_fp_outside_euro',
                'tax_src_id': f'account.{cid}_purchase_tax_6_services',
                'tax_dest_id': f'account.{cid}_purchase_services_tax_6_NEC',
            },
            f'{cid}_fpp_outside_6_goods': {
                'position_id': f'account.{cid}_fp_outside_euro',
                'tax_src_id': f'account.{cid}_purchase_tax_6_goods',
                'tax_dest_id': f'account.{cid}_purchase_goods_tax_6_NEC',
            },
            f'{cid}_fps_outside_25_services': {
                'position_id': f'account.{cid}_fp_outside_euro',
                'tax_src_id': f'account.{cid}_sale_tax_25_services',
                'tax_dest_id': f'account.{cid}_sale_tax_services_NEC',
            },
            f'{cid}_fps_outside_25_goods': {
                'position_id': f'account.{cid}_fp_outside_euro',
                'tax_src_id': f'account.{cid}_sale_tax_25_goods',
                'tax_dest_id': f'account.{cid}_sale_tax_goods_NEC',
            },
            f'{cid}_fps_outside_12_services': {
                'position_id': f'account.{cid}_fp_outside_euro',
                'tax_src_id': f'account.{cid}_sale_tax_12_services',
                'tax_dest_id': f'account.{cid}_sale_tax_services_NEC',
            },
            f'{cid}_fps_outside_12_goods': {
                'position_id': f'account.{cid}_fp_outside_euro',
                'tax_src_id': f'account.{cid}_sale_tax_12_goods',
                'tax_dest_id': f'account.{cid}_sale_tax_goods_NEC',
            },
            f'{cid}_fps_outside_6_services': {
                'position_id': f'account.{cid}_fp_outside_euro',
                'tax_src_id': f'account.{cid}_sale_tax_6_services',
                'tax_dest_id': f'account.{cid}_sale_tax_services_NEC',
            },
            f'{cid}_fps_outside_6_goods': {
                'position_id': f'account.{cid}_fp_outside_euro',
                'tax_src_id': f'account.{cid}_sale_tax_6_goods',
                'tax_dest_id': f'account.{cid}_sale_tax_goods_NEC',
            }
        }

    def _get_se_fiscal_position_account(self, template_code, company):
        cid = (company or self.env.company).id
        return {
            f'{cid}_fps_euro_25_goods_acc': {
                'position_id': f'account.{cid}_fp_euro_b2b',
                'account_src_id': f'account.{cid}_a3001',
                'account_dest_id': f'account.{cid}_a3106',
            },
            f'{cid}_fps_euro_12_goods_acc': {
                'position_id': f'account.{cid}_fp_euro_b2b',
                'account_src_id': f'account.{cid}_a3002',
                'account_dest_id': f'account.{cid}_a3106',
            },
            f'{cid}_fps_euro_6_goods_acc': {
                'position_id': f'account.{cid}_fp_euro_b2b',
                'account_src_id': f'account.{cid}_a3003',
                'account_dest_id': f'account.{cid}_a3106',
            },
            f'{cid}_fps_euro_0_goods_acc': {
                'position_id': f'account.{cid}_fp_euro_b2b',
                'account_src_id': f'account.{cid}_a3004',
                'account_dest_id': f'account.{cid}_a3106',
            },
            f'{cid}_fps_euro_25_service_acc': {
                'position_id': f'account.{cid}_fp_euro_b2b',
                'account_src_id': f'account.{cid}_a3001',
                'account_dest_id': f'account.{cid}_a3308',
            },
            f'{cid}_fps_euro_12_service_acc': {
                'position_id': f'account.{cid}_fp_euro_b2b',
                'account_src_id': f'account.{cid}_a3002',
                'account_dest_id': f'account.{cid}_a3308',
            },
            f'{cid}_fps_euro_6_service_acc': {
                'position_id': f'account.{cid}_fp_euro_b2b',
                'account_src_id': f'account.{cid}_a3003',
                'account_dest_id': f'account.{cid}_a3308',
            },
            f'{cid}_fps_euro_0_service_acc': {
                'position_id': f'account.{cid}_fp_euro_b2b',
                'account_src_id': f'account.{cid}_a3004',
                'account_dest_id': f'account.{cid}_a3308',
            },
            f'{cid}_fps_outside_euro_25_goods_acc': {
                'position_id': f'account.{cid}_fp_outside_euro',
                'account_src_id': f'account.{cid}_a3001',
                'account_dest_id': f'account.{cid}_a3105',
            },
            f'{cid}_fps_outside_euro_12_goods_acc': {
                'position_id': f'account.{cid}_fp_outside_euro',
                'account_src_id': f'account.{cid}_a3002',
                'account_dest_id': f'account.{cid}_a3105',
            },
            f'{cid}_fps_outside_euro_6_goods_acc': {
                'position_id': f'account.{cid}_fp_outside_euro',
                'account_src_id': f'account.{cid}_a3003',
                'account_dest_id': f'account.{cid}_a3105',
            },
            f'{cid}_fps_outside_euro_0_goods_acc': {
                'position_id': f'account.{cid}_fp_outside_euro',
                'account_src_id': f'account.{cid}_a3004',
                'account_dest_id': f'account.{cid}_a3105',
            },
            f'{cid}_fps_outside_euro_25_service_acc': {
                'position_id': f'account.{cid}_fp_outside_euro',
                'account_src_id': f'account.{cid}_a3001',
                'account_dest_id': f'account.{cid}_a3305',
            },
            f'{cid}_fps_outside_euro_12_service_acc': {
                'position_id': f'account.{cid}_fp_outside_euro',
                'account_src_id': f'account.{cid}_a3002',
                'account_dest_id': f'account.{cid}_a3305',
            },
            f'{cid}_fps_outside_euro_6_service_acc': {
                'position_id': f'account.{cid}_fp_outside_euro',
                'account_src_id': f'account.{cid}_a3003',
                'account_dest_id': f'account.{cid}_a3305',
            },
            f'{cid}_fps_outside_euro_0_service_acc': {
                'position_id': f'account.{cid}_fp_outside_euro',
                'account_src_id': f'account.{cid}_a3004',
                'account_dest_id': f'account.{cid}_a3305',
            }
        }
