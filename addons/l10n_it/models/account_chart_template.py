# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, Command

class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    def _get_be_chart_template_data(self, template_code, company):
        res = self._get_chart_template_data(template_code, company)
        if template_code == 'it':
            res['account.fiscal.position'] = self._get_it_fiscal_position(template_code, company)
        return res

    def _get_it_template_data(self, template_code, company):
        cid = (company or self.env.company).id
        return {
            'cash_account_code_prefix': '180',
            'bank_account_code_prefix': '182',
            'transfer_account_code_prefix': '183',
            'property_account_receivable_id': f'account.{cid}_1501',
            'property_account_payable_id': f'account.{cid}_2501',
            'property_account_expense_categ_id': f'account.{cid}_4101',
            'property_account_income_categ_id': f'account.{cid}_3101',
            'property_tax_payable_account_id': f'account.{cid}_2605',
            'property_tax_receivable_account_id': f'account.{cid}_2605',
        }

    def _get_it_account_tax(self, template_code, company):
        cid = (company or self.env.company).id
        tags = self._get_tag_mapper(template_code)
        return {
            f'{cid}_22v': {
                'description': '22v',
                'name': 'Iva al 22% (debito)',
                'sequence': 1,
                'amount': 22.0,
                'amount_type': 'percent',
                'type_tax_use': 'sale',
                'price_include': False,
                'tax_group_id': f'account.{cid}_tax_group_iva_22',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+02'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_2601',
                        'tag_ids': tags('+04'),
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
                        'account_id': f'account.{cid}_2601',
                    }),
                ],
            },
            f'{cid}_22a': {
                'description': '22a',
                'name': 'Iva al 22% (credito)',
                'sequence': 2,
                'amount': 22.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'price_include': False,
                'tax_group_id': f'account.{cid}_tax_group_iva_22',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+03'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_1601',
                        'tag_ids': tags('+05'),
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
                        'account_id': f'account.{cid}_1601',
                    }),
                ],
            },
            f'{cid}_10v': {
                'description': '10v',
                'name': 'Iva al 10% (debito)',
                'sequence': 5,
                'amount': 10.0,
                'amount_type': 'percent',
                'type_tax_use': 'sale',
                'price_include': False,
                'tax_group_id': f'account.{cid}_tax_group_iva_10',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+02'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_2601',
                        'tag_ids': tags('+04'),
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
                        'account_id': f'account.{cid}_2601',
                    }),
                ],
            },
            f'{cid}_10a': {
                'description': '10a',
                'name': 'Iva al 10% (credito)',
                'sequence': 6,
                'amount': 10.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'price_include': False,
                'tax_group_id': f'account.{cid}_tax_group_iva_10',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+03'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_1601',
                        'tag_ids': tags('+05'),
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
                        'account_id': f'account.{cid}_1601',
                    }),
                ],
            },
            f'{cid}_5v': {
                'description': '5v',
                'name': 'Iva al 5% (debito)',
                'sequence': 5,
                'amount': 5.0,
                'amount_type': 'percent',
                'type_tax_use': 'sale',
                'price_include': False,
                'tax_group_id': f'account.{cid}_tax_group_iva_5',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+02'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_2601',
                        'tag_ids': tags('+04'),
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
                        'account_id': f'account.{cid}_2601',
                    }),
                ],
            },
            f'{cid}_5a': {
                'description': '5a',
                'name': 'Iva al 5% (credito)',
                'sequence': 6,
                'amount': 5.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'price_include': False,
                'tax_group_id': f'account.{cid}_tax_group_iva_5',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+03'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_1601',
                        'tag_ids': tags('+05'),
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
                        'account_id': f'account.{cid}_1601',
                    }),
                ],
            },
            f'{cid}_4v': {
                'description': '4v',
                'name': 'Iva al 4% (debito)',
                'sequence': 17,
                'amount': 4.0,
                'amount_type': 'percent',
                'type_tax_use': 'sale',
                'price_include': False,
                'tax_group_id': f'account.{cid}_tax_group_iva_4',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+02'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_2601',
                        'tag_ids': tags('+04'),
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
                        'account_id': f'account.{cid}_2601',
                    }),
                ],
            },
            f'{cid}_4a': {
                'description': '4a',
                'name': 'Iva al 4% (credito)',
                'sequence': 18,
                'amount': 4.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'price_include': False,
                'tax_group_id': f'account.{cid}_tax_group_iva_4',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+03'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_1601',
                        'tag_ids': tags('+05'),
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
                        'account_id': f'account.{cid}_1601',
                    }),
                ],
            },
            f'{cid}_00v': {
                'description': '00v',
                'name': 'Fuori Campo IVA (debito)',
                'sequence': 22,
                'amount': 0.0,
                'amount_type': 'percent',
                'type_tax_use': 'sale',
                'price_include': False,
                'tax_group_id': f'account.{cid}_tax_group_fuori',
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
            f'{cid}_00a': {
                'description': '00a',
                'name': 'Fuori Campo IVA (credito)',
                'sequence': 23,
                'amount': 0.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'price_include': False,
                'tax_group_id': f'account.{cid}_tax_group_fuori',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+02'),
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
            f'{cid}_00art15v': {
                'description': '00art15v',
                'name': 'Imponibile Escluso Art.15 (debito)',
                'sequence': 22,
                'amount': 0.0,
                'amount_type': 'percent',
                'type_tax_use': 'sale',
                'price_include': False,
                'tax_group_id': f'account.{cid}_tax_group_imp_esc_art_15',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_vp2',
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
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_00art15a': {
                'description': '00art15a',
                'name': 'Imponibile Escluso Art.15 (credito)',
                'sequence': 23,
                'amount': 0.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'price_include': False,
                'tax_group_id': f'account.{cid}_tax_group_imp_esc_art_15',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+03'),
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
            }
        }

    def _get_it_res_company(self, template_code, company):
        company = (company or self.env.company)
        cid = company.id
        return {
            company.get_external_id()[company.id]: {
                'currency_id': 'base.EUR',
                'account_fiscal_country_id': 'base.it',
                'account_default_pos_receivable_account_id': f'account.{cid}_1508',
                'income_currency_exchange_account_id': f'account.{cid}_3220',
                'expense_currency_exchange_account_id': f'account.{cid}_4920',
            }
        }

    def _get_it_fiscal_position(self, template_code, company):
        cid = (company or self.env.company).id
        return {
            f'{cid}_account_fiscal_position_0': {
                'name': 'Italia',
                'id': 'it',
                'sequence': 1,
                'auto_apply': 1,
                'vat_required': 1,
                'country_id': 'base.it',
            },
            f'{cid}_account_fiscal_position_1': {
                'name': 'Regime Extra comunitario',
                'id': 'extra',
                'sequence': 4,
                'auto_apply': 1,
            },
            f'{cid}_account_fiscal_position_2': {
                'name': 'Regime Intra comunitario privato',
                'id': 'intra_private',
                'sequence': 2,
                'auto_apply': 1,
                'country_group_id': 'base.europe',
            },
            f'{cid}_account_fiscal_position_3': {
                'name': 'Regime Intra comunitario',
                'id': 'intra',
                'sequence': 3,
                'auto_apply': 1,
                'vat_required': 1,
                'country_group_id': 'base.europe',
            }
        }
