# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, Command, _

class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    def _get_be_chart_template_data(self, template_code, company):
        res = self._get_chart_template_data(template_code, company)
        if template_code == 'be':
            res['account.fiscal.position'] = self._get_be_fiscal_position(template_code, company)
            res['account.reconcile.model'] = self._get_be_reconcile_model(template_code, company)
            res['account.reconcile.model.line'] = self._get_be_reconcile_model_line(template_code, company)
            res['account.fiscal.position.tax'] = self._get_be_fiscal_position_tax(template_code, company)
        return res

    def _get_be_template_data(self, template_code, company):
        cid = (company or self.env.company).id
        return {
            'bank_account_code_prefix': '550',
            'cash_account_code_prefix': '570',
            'transfer_account_code_prefix': '580',
            'spoken_languages': 'nl_BE;nl_NL;fr_FR;fr_BE;de_DE',
            'code_digits': '6',
            'property_account_receivable_id': f'account.{cid}_a400',
            'property_account_payable_id': f'account.{cid}_a440',
            'property_account_expense_categ_id': f'account.{cid}_a600',
            'property_account_income_categ_id': f'account.{cid}_a7000',
            'property_tax_payable_account_id': f'account.{cid}_a4512',
            'property_tax_receivable_account_id': f'account.{cid}_a4112',
            'account_journal_suspense_account_id': f'account.{cid}_a499',
        }

    def _get_be_account_journal(self, template_code, company):
        cid = company.id
        data = self._get_account_journal(template_code, company)
        data[f"{cid}_sale"].update({
            'default_account_id': f'account.{cid}_a7000',
            'refund_sequence':  True
        })
        data[f"{cid}_purchase"].update({
            'default_account_id': f'account.{cid}_a600',
            'refund_sequence': True
        })
        data[f"{cid}_cash"]['suspense_account_id'] = f'account.{cid}_a499'
        data[f"{cid}_bank"]['suspense_account_id'] = f'account.{cid}_a499'
        return data

    def _get_be_fiscal_position(self, template_code, company):
        cid = company.id
        return {
            f"{cid}_fiscal_position_template_1": {
                'sequence': 1,
                'name': _("Régime National"),
                'auto_apply': True,
                'vat_required': True,
                'country_id': 'base.be',
            },
            f"{cid}_fiscal_position_template_5": {
                'sequence': 2,
                'name': _("EU privé"),
                'auto_apply': True,
                'country_group_id': 'base.europe',
            },
            f"{cid}_fiscal_position_template_3": {
                'sequence': 3,
                'name': _("Régime Intra-Communautaire"),
                'auto_apply': True,
                'vat_required': True,
                'country_group_id': 'base.europe',
                'account_ids': [
                    Command.create({
                        'account_src_id': f'account.{cid}_a7000',
                        'account_dest_id': f'account.{cid}_a7001',
                    }),
                    Command.create({
                        'account_src_id': f'account.{cid}_a7010',
                        'account_dest_id': f'account.{cid}_a7011',
                    }),
                    Command.create({
                        'account_src_id': f'account.{cid}_a7050',
                        'account_dest_id': f'account.{cid}_a7051',
                    }),
                ],
                'tax_ids': [
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-OUT-00-S',
                        'tax_dest_id': f'account.{cid}_attn_VAT-OUT-00-EU-S',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-OUT-00-L',
                        'tax_dest_id': f'account.{cid}_attn_VAT-OUT-00-EU-L',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-OUT-06-S',
                        'tax_dest_id': f'account.{cid}_attn_VAT-OUT-00-EU-S',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-OUT-06-L',
                        'tax_dest_id': f'account.{cid}_attn_VAT-OUT-00-EU-L',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-OUT-12-S',
                        'tax_dest_id': f'account.{cid}_attn_VAT-OUT-00-EU-S',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-OUT-12-L',
                        'tax_dest_id': f'account.{cid}_attn_VAT-OUT-00-EU-L',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-OUT-21-S',
                        'tax_dest_id': f'account.{cid}_attn_VAT-OUT-00-EU-S',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-OUT-21-L',
                        'tax_dest_id': f'account.{cid}_attn_VAT-OUT-00-EU-L',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-IN-V81-00',
                        'tax_dest_id': f'account.{cid}_attn_VAT-IN-V81-00-EU',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-IN-V81-06',
                        'tax_dest_id': f'account.{cid}_attn_VAT-IN-V81-06-EU',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-IN-V81-12',
                        'tax_dest_id': f'account.{cid}_attn_VAT-IN-V81-12-EU',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-IN-V81-21',
                        'tax_dest_id': f'account.{cid}_attn_VAT-IN-V81-21-EU',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-IN-V82-00-S',
                        'tax_dest_id': f'account.{cid}_attn_VAT-IN-V82-00-EU-S',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-IN-V82-00-G',
                        'tax_dest_id': f'account.{cid}_attn_VAT-IN-V82-00-EU-G',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-IN-V82-06-S',
                        'tax_dest_id': f'account.{cid}_attn_VAT-IN-V82-06-EU-S',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-IN-V82-06-G',
                        'tax_dest_id': f'account.{cid}_attn_VAT-IN-V82-06-EU-G',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-IN-V82-12-S',
                        'tax_dest_id': f'account.{cid}_attn_VAT-IN-V82-12-EU-S',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-IN-V82-12-G',
                        'tax_dest_id': f'account.{cid}_attn_VAT-IN-V82-12-EU-G',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-IN-V82-21-S',
                        'tax_dest_id': f'account.{cid}_attn_VAT-IN-V82-21-EU-S',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-IN-V82-21-G',
                        'tax_dest_id': f'account.{cid}_attn_VAT-IN-V82-21-EU-G',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-IN-V83-00',
                        'tax_dest_id': f'account.{cid}_attn_VAT-IN-V83-00-EU',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-IN-V83-06',
                        'tax_dest_id': f'account.{cid}_attn_VAT-IN-V83-06-EU',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-IN-V83-12',
                        'tax_dest_id': f'account.{cid}_attn_VAT-IN-V83-12-EU',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-IN-V83-21',
                        'tax_dest_id': f'account.{cid}_attn_VAT-IN-V83-21-EU',
                    }),
                ],
            },
            f"{cid}_fiscal_position_template_2": {
                'sequence': 4,
                'name': _("Régime Extra-Communautaire"),
                'auto_apply': True,
                'account_ids': [
                    Command.create({
                        'account_src_id': f'account.{cid}_a7000',
                        'account_dest_id': f'account.{cid}_a7002',
                    }),
                    Command.create({
                        'account_src_id': f'account.{cid}_a7010',
                        'account_dest_id': f'account.{cid}_a7012',
                    }),
                    Command.create({
                        'account_src_id': f'account.{cid}_a7050',
                        'account_dest_id': f'account.{cid}_a7052',
                    }),
                ],
                'tax_ids': [
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-OUT-00-S',
                        'tax_dest_id': f'account.{cid}_attn_VAT-OUT-00-ROW',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-OUT-00-L',
                        'tax_dest_id': f'account.{cid}_attn_VAT-OUT-00-ROW',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-OUT-06-S',
                        'tax_dest_id': f'account.{cid}_attn_VAT-OUT-00-ROW',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-OUT-06-L',
                        'tax_dest_id': f'account.{cid}_attn_VAT-OUT-00-ROW',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-OUT-12-S',
                        'tax_dest_id': f'account.{cid}_attn_VAT-OUT-00-ROW',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-OUT-12-L',
                        'tax_dest_id': f'account.{cid}_attn_VAT-OUT-00-ROW',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-OUT-21-S',
                        'tax_dest_id': f'account.{cid}_attn_VAT-OUT-00-ROW',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-OUT-21-L',
                        'tax_dest_id': f'account.{cid}_attn_VAT-OUT-00-ROW',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-IN-V81-06',
                        'tax_dest_id': f'account.{cid}_attn_VAT-IN-V81-06-ROW-CC',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-IN-V81-12',
                        'tax_dest_id': f'account.{cid}_attn_VAT-IN-V81-12-ROW-CC',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-IN-V81-21',
                        'tax_dest_id': f'account.{cid}_attn_VAT-IN-V81-21-ROW-CC',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-IN-V82-06-S',
                        'tax_dest_id': f'account.{cid}_attn_VAT-IN-V82-06-ROW-CC',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-IN-V82-06-G',
                        'tax_dest_id': f'account.{cid}_attn_VAT-IN-V82-06-ROW-CC',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-IN-V82-12-S',
                        'tax_dest_id': f'account.{cid}_attn_VAT-IN-V82-12-ROW-CC',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-IN-V82-12-G',
                        'tax_dest_id': f'account.{cid}_attn_VAT-IN-V82-12-ROW-CC',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-IN-V82-21-S',
                        'tax_dest_id': f'account.{cid}_attn_VAT-IN-V82-21-ROW-CC',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-IN-V82-21-G',
                        'tax_dest_id': f'account.{cid}_attn_VAT-IN-V82-21-ROW-CC',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-IN-V83-06',
                        'tax_dest_id': f'account.{cid}_attn_VAT-IN-V83-06-ROW-CC',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-IN-V83-12',
                        'tax_dest_id': f'account.{cid}_attn_VAT-IN-V83-12-ROW-CC',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-IN-V83-21',
                        'tax_dest_id': f'account.{cid}_attn_VAT-IN-V83-21-ROW-CC',
                    }),
                ]
            },
            f"{cid}_fiscal_position_template_4": {
                'name': _("Régime Cocontractant"),
                'sequence': 5,
                'tax_ids': [
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-OUT-00-S',
                        'tax_dest_id': f'account.{cid}_attn_VAT-OUT-00-CC',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-OUT-00-L',
                        'tax_dest_id': f'account.{cid}_attn_VAT-OUT-00-CC',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-OUT-06-S',
                        'tax_dest_id': f'account.{cid}_attn_VAT-OUT-00-CC',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-OUT-06-L',
                        'tax_dest_id': f'account.{cid}_attn_VAT-OUT-00-CC',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-OUT-12-S',
                        'tax_dest_id': f'account.{cid}_attn_VAT-OUT-00-CC',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-OUT-12-L',
                        'tax_dest_id': f'account.{cid}_attn_VAT-OUT-00-CC',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-OUT-21-S',
                        'tax_dest_id': f'account.{cid}_attn_VAT-OUT-00-CC',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-OUT-21-L',
                        'tax_dest_id': f'account.{cid}_attn_VAT-OUT-00-CC',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-IN-V81-06',
                        'tax_dest_id': f'account.{cid}_attn_VAT-IN-V81-06-CC',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-IN-V81-12',
                        'tax_dest_id': f'account.{cid}_attn_VAT-IN-V81-12-CC',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-IN-V81-21',
                        'tax_dest_id': f'account.{cid}_attn_VAT-IN-V81-21-CC',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-IN-V82-06-S',
                        'tax_dest_id': f'account.{cid}_attn_VAT-IN-V82-06-CC',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-IN-V82-06-G',
                        'tax_dest_id': f'account.{cid}_attn_VAT-IN-V82-06-CC',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-IN-V82-12-S',
                        'tax_dest_id': f'account.{cid}_attn_VAT-IN-V82-12-CC',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-IN-V82-12-G',
                        'tax_dest_id': f'account.{cid}_attn_VAT-IN-V82-12-CC',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-IN-V82-21-S',
                        'tax_dest_id': f'account.{cid}_attn_VAT-IN-V82-21-CC',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-IN-V82-21-G',
                        'tax_dest_id': f'account.{cid}_attn_VAT-IN-V82-21-CC',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-IN-V83-06',
                        'tax_dest_id': f'account.{cid}_attn_VAT-IN-V83-06-CC',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-IN-V83-12',
                        'tax_dest_id': f'account.{cid}_attn_VAT-IN-V83-12-CC',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-IN-V83-21',
                        'tax_dest_id': f'account.{cid}_attn_VAT-IN-V83-21-CC',
                    }),
                ]
            },
        }

    def _get_be_reconcile_model(self, template_code, company):
        cid = company.id
        return {
            f"{cid}_escompte_template": {
                'name': _("Escompte"),
                'line_ids': [
                    Command.create({
                        'account_id': f'account.{cid}_a653',
                        'amount_type': 'percentage',
                        'amount_string': '100',
                        'label': _("Escompte accordé"),
                    }),
                ],
            },
            f"{cid}_frais_bancaires_htva_template": {
                'name': _("Frais bancaires HTVA"),
                'line_ids': [
                    Command.create({
                        'account_id': f'account.{cid}_a6560',
                        'amount_type': 'percentage',
                        'amount_string': '100',
                        'label': _("Frais bancaires HTVA"),
                    }),
                ],
            },
            f"{cid}_frais_bancaires_tva21_template": {
                'name': _("Frais bancaires TVA21"),
                'line_ids': [
                    Command.create({
                        'account_id': f'account.{cid}_a6560',
                        'amount_type': 'percentage',
                        'amount_string': '100',
                        'label': _("Frais bancaires TVA21"),
                        'tax_ids': [
                            Command.set([f'account.{cid}_attn_TVA-21-inclus-dans-prix']),
                        ]
                    }),
                ],
            },
            f"{cid}_virements_internes_template": {
                'name': _("Virements internes"),
                'line_ids': [
                    Command.create({
                        'account_id': self.env['account.account'].search([
                            ('code', '=like', self._get_template_data(template_code, company)['transfer_account_code_prefix'] + '%'),
                            ('company_id', '=', cid)
                        ]).id,
                        'amount_type': 'percentage',
                        'amount_string': '100',
                        'label': _("Virements internes"),
                    }),
                ],
            },
        }

    def _get_be_account_tax(self, template_code, company):
        cid = (company or self.env.company).id
        tags = self._get_tag_mapper(template_code)
        return {
            f'{cid}_attn_VAT-OUT-21-L': {
                'sequence': 10,
                'description': '21%',
                'name': '21%',
                'price_include': False,
                'amount': 21.0,
                'amount_type': 'percent',
                'type_tax_use': 'sale',
                'tax_group_id': f'account.{cid}_tax_group_tva_21',
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
                        'account_id': f'account.{cid}_a451',
                        'tag_ids': tags('+54'),
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+49'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451',
                        'tag_ids': tags('+64'),
                    }),
                ],
            },
            f'{cid}_attn_VAT-OUT-21-S': {
                'sequence': 11,
                'description': '21%',
                'name': '21% S',
                'price_include': False,
                'amount': 21.0,
                'amount_type': 'percent',
                'type_tax_use': 'sale',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_21',
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
                        'account_id': f'account.{cid}_a451',
                        'tag_ids': tags('+54'),
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+49'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451',
                        'tag_ids': tags('+64'),
                    }),
                ],
            },
            f'{cid}_attn_VAT-OUT-12-S': {
                'sequence': 20,
                'description': '12%',
                'name': '12% S',
                'price_include': False,
                'amount': 12.0,
                'amount_type': 'percent',
                'type_tax_use': 'sale',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_12',
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
                        'account_id': f'account.{cid}_a451',
                        'tag_ids': tags('+54'),
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+49'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451',
                        'tag_ids': tags('+64'),
                    }),
                ],
            },
            f'{cid}_attn_VAT-OUT-12-L': {
                'sequence': 21,
                'description': '12%',
                'name': '12%',
                'price_include': False,
                'amount': 12.0,
                'amount_type': 'percent',
                'type_tax_use': 'sale',
                'tax_group_id': f'account.{cid}_tax_group_tva_12',
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
                        'account_id': f'account.{cid}_a451',
                        'tag_ids': tags('+54'),
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+49'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451',
                        'tag_ids': tags('+64'),
                    }),
                ],
            },
            f'{cid}_attn_VAT-OUT-06-S': {
                'sequence': 30,
                'description': '6%',
                'name': '6% S',
                'price_include': False,
                'amount': 6.0,
                'amount_type': 'percent',
                'type_tax_use': 'sale',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_6',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+01'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451',
                        'tag_ids': tags('+54'),
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+49'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451',
                        'tag_ids': tags('+64'),
                    }),
                ],
            },
            f'{cid}_attn_VAT-OUT-06-L': {
                'sequence': 31,
                'description': '6%',
                'name': '6%',
                'price_include': False,
                'amount': 6.0,
                'amount_type': 'percent',
                'type_tax_use': 'sale',
                'tax_group_id': f'account.{cid}_tax_group_tva_6',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+01'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451',
                        'tag_ids': tags('+54'),
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+49'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451',
                        'tag_ids': tags('+64'),
                    }),
                ],
            },
            f'{cid}_attn_VAT-OUT-00-S': {
                'sequence': 40,
                'description': '0%',
                'name': '0% S.',
                'price_include': False,
                'amount': 0.0,
                'amount_type': 'percent',
                'type_tax_use': 'sale',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_0',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+00'),
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
                        'tag_ids': tags('+49'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-OUT-00-L': {
                'sequence': 41,
                'description': '0%',
                'name': '0%',
                'price_include': False,
                'amount': 0.0,
                'amount_type': 'percent',
                'type_tax_use': 'sale',
                'tax_group_id': f'account.{cid}_tax_group_tva_0',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+00'),
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
                        'tag_ids': tags('+49'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-OUT-00-CC': {
                'sequence': 50,
                'description': '0%',
                'name': '0% Cocont',
                'price_include': False,
                'amount': 0.0,
                'amount_type': 'percent',
                'type_tax_use': 'sale',
                'tax_group_id': f'account.{cid}_tax_group_tva_0',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+45'),
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
                        'tag_ids': tags('+49'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-OUT-00-EU-S': {
                'sequence': 60,
                'description': '0%',
                'name': '0% EU S',
                'price_include': False,
                'amount': 0.0,
                'amount_type': 'percent',
                'type_tax_use': 'sale',
                'tax_group_id': f'account.{cid}_tax_group_tva_0',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+44'),
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
                        'tag_ids': tags('+48s44'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-OUT-00-EU-L': {
                'sequence': 61,
                'description': '0%',
                'name': '0% EU M',
                'price_include': False,
                'amount': 0.0,
                'amount_type': 'percent',
                'type_tax_use': 'sale',
                'tax_group_id': f'account.{cid}_tax_group_tva_0',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+46L'),
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
                        'tag_ids': tags('+48s46L'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-OUT-00-EU-T': {
                'sequence': 62,
                'description': '0%',
                'name': '0% EU T',
                'price_include': False,
                'amount': 0.0,
                'amount_type': 'percent',
                'type_tax_use': 'sale',
                'tax_group_id': f'account.{cid}_tax_group_tva_0',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+46T'),
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
                        'tag_ids': tags('+48s46T'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-OUT-00-ROW': {
                'sequence': 70,
                'description': '0%',
                'name': '0% EX',
                'price_include': False,
                'amount': 0.0,
                'amount_type': 'percent',
                'type_tax_use': 'sale',
                'tax_group_id': f'account.{cid}_tax_group_tva_0',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+47'),
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
                        'tag_ids': tags('+49'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V81-21': {
                'sequence': 110,
                'description': '21%',
                'name': '21% M',
                'price_include': False,
                'amount': 21.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'tax_group_id': f'account.{cid}_tax_group_tva_21',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+81'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'tag_ids': tags('+59'),
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('-81', '+85'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'tag_ids': tags('+63'),
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V81-12': {
                'sequence': 120,
                'description': '12%',
                'name': '12% M',
                'price_include': False,
                'amount': 12.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'tax_group_id': f'account.{cid}_tax_group_tva_12',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+81'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'tag_ids': tags('+59'),
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('-81', '+85'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'tag_ids': tags('+63'),
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V81-06': {
                'sequence': 130,
                'description': '6%',
                'name': '6% M',
                'price_include': False,
                'amount': 6.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'tax_group_id': f'account.{cid}_tax_group_tva_6',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+81'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'tag_ids': tags('+59'),
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('-81', '+85'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'tag_ids': tags('+63'),
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V81-00': {
                'sequence': 140,
                'description': '0%',
                'name': '0% M',
                'price_include': False,
                'amount': 0.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'tax_group_id': f'account.{cid}_tax_group_tva_0',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+81'),
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
                        'tag_ids': tags('-81', '+85'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_TVA-21-inclus-dans-prix': {
                'sequence': 150,
                'description': '21%',
                'name': '21% S.TTC',
                'price_include': True,
                'amount': 21.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'tax_group_id': f'account.{cid}_tax_group_tva_21',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+82'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'tag_ids': tags('+59'),
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('-82', '+85'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'tag_ids': tags('+63'),
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V82-21-S': {
                'sequence': 210,
                'description': '21%',
                'name': '21% S',
                'price_include': False,
                'amount': 21.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_21',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+82'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'tag_ids': tags('+59'),
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('-82', '+85'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'tag_ids': tags('+63'),
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V82-21-G': {
                'sequence': 220,
                'description': '21%',
                'name': '21% G',
                'price_include': False,
                'amount': 21.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_21',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+82'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'tag_ids': tags('+59'),
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('-82', '+85'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'tag_ids': tags('+63'),
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V82-12-S': {
                'sequence': 230,
                'description': '12%',
                'name': '12% S',
                'price_include': False,
                'amount': 12.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_12',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+82'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'tag_ids': tags('+59'),
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('-82', '+85'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'tag_ids': tags('+63'),
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V82-12-G': {
                'sequence': 240,
                'description': '12%',
                'name': '12% G',
                'price_include': False,
                'amount': 12.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_12',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+82'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'tag_ids': tags('+59'),
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('-82', '+85'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'tag_ids': tags('+63'),
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V82-06-S': {
                'sequence': 250,
                'description': '6%',
                'name': '6% S',
                'price_include': False,
                'amount': 6.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_6',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+82'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'tag_ids': tags('+59'),
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('-82', '+85'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'tag_ids': tags('+63'),
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V82-06-G': {
                'sequence': 260,
                'description': '6%',
                'name': '6% G',
                'price_include': False,
                'amount': 6.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_6',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+82'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'tag_ids': tags('+59'),
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('-82', '+85'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'tag_ids': tags('+63'),
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V82-00-S': {
                'sequence': 270,
                'description': '0%',
                'name': '0% S',
                'price_include': False,
                'amount': 0.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_0',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+82'),
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
                        'tag_ids': tags('-82', '+85'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V82-00-G': {
                'sequence': 280,
                'description': '0%',
                'name': '0% G',
                'price_include': False,
                'amount': 0.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_0',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+82'),
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
                        'tag_ids': tags('-82', '+85'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V83-21': {
                'sequence': 310,
                'description': '21%',
                'name': "21% IG",
                'price_include': False,
                'amount': 21.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_21',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+83'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'tag_ids': tags('+59'),
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('-83', '+85'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'tag_ids': tags('+63'),
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V83-12': {
                'sequence': 320,
                'description': '12%',
                'name': "12% IG",
                'price_include': False,
                'amount': 12.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_12',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+83'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'tag_ids': tags('+59'),
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('-83', '+85'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'tag_ids': tags('+63'),
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V83-06': {
                'sequence': 330,
                'description': '6%',
                'name': "6% IG",
                'price_include': False,
                'amount': 6.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_6',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+83'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'tag_ids': tags('+59'),
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('-83', '+85'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'tag_ids': tags('+63'),
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V83-00': {
                'sequence': 340,
                'description': '0%',
                'name': "0% IG",
                'price_include': False,
                'amount': 0.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_0',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+83'),
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
                        'tag_ids': tags('-83', '+85'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V81-21-CC': {
                'sequence': 410,
                'description': '21%',
                'name': '21% M.Cocont',
                'price_include': False,
                'amount': 21.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'tax_group_id': f'account.{cid}_tax_group_tva_21',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+81', '+87'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'tag_ids': tags('+59'),
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451056',
                        'tag_ids': tags('-56'),
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('-81', '-87', '+85'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451056',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V81-12-CC': {
                'sequence': 420,
                'description': '12%',
                'name': '12% M.Cocont',
                'price_include': False,
                'amount_type': 'percent',
                'amount': 12.0,
                'type_tax_use': 'purchase',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_12',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+81', '+87'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'tag_ids': tags('+59'),
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451056',
                        'tag_ids': tags('-56'),
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('-81', '-87', '+85'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451056',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V81-06-CC': {
                'sequence': 430,
                'description': '6%',
                'name': '6% M.Cocont',
                'price_include': False,
                'amount_type': 'percent',
                'amount': 6.0,
                'type_tax_use': 'purchase',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_6',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+81', '+87'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'tag_ids': tags('+59'),
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451056',
                        'tag_ids': tags('-56'),
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('-81', '-87', '+85'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451056',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V81-00-CC': {
                'sequence': 440,
                'description': '0%',
                'name': '0% M.Cocont',
                'price_include': False,
                'amount': 0.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_0',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+81', '+87'),
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
                        'tag_ids': tags('-81', '-87', '+85'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V82-21-CC': {
                'sequence': 510,
                'description': '21%',
                'name': '21% S.Cocont',
                'price_include': False,
                'amount': 21.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_21',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+82', '+87'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'tag_ids': tags('+59'),
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451056',
                        'tag_ids': tags('-56'),
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('-82', '-87', '+85'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451056',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V82-12-CC': {
                'sequence': 520,
                'description': '12%',
                'name': '12% S.Cocont',
                'price_include': False,
                'amount': 12.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_12',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+82', '+87'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'tag_ids': tags('+59'),
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451056',
                        'tag_ids': tags('-56'),
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('-82', '-87', '+85'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451056',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V82-06-CC': {
                'sequence': 530,
                'description': '6%',
                'name': '6% S.Cocont',
                'price_include': False,
                'amount': 6.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_6',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+82', '+87'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'tag_ids': tags('+59'),
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451056',
                        'tag_ids': tags('-56'),
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('-82', '-87', '+85'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451056',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V82-00-CC': {
                'sequence': 540,
                'description': '0%',
                'name': '0% S.Cocont',
                'price_include': False,
                'amount': 0.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_0',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+82', '+87'),
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
                        'tag_ids': tags('-82', '-87', '+85'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V83-21-CC': {
                'sequence': 610,
                'description': '21%',
                'name': "21% IG.Cocont",
                'price_include': False,
                'amount': 21.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_21',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+83', '+87'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'tag_ids': tags('+59'),
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451056',
                        'tag_ids': tags('-56'),
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('-83', '-87', '+85'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451056',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V83-12-CC': {
                'sequence': 620,
                'description': '12%',
                'name': "12% IG.Cocont",
                'price_include': False,
                'amount': 12.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_12',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+83', '+87'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'tag_ids': tags('+59'),
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451056',
                        'tag_ids': tags('-56'),
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('-83', '-87', '+85'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451056',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V83-06-CC': {
                'sequence': 630,
                'description': '6%',
                'name': "6% IG.Cocont",
                'price_include': False,
                'amount': 6.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_6',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+83', '+87'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'tag_ids': tags('+59'),
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451056',
                        'tag_ids': tags('-56'),
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('-83', '-87', '+85'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451056',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V83-00-CC': {
                'sequence': 640,
                'description': '0%',
                'name': "0% IG.Cocont",
                'price_include': False,
                'amount': 0.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_0',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+83', '+87'),
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
                        'tag_ids': tags('-83', '-87', '+85'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V82-CAR-EXC': {
                'sequence': 720,
                'description': '21%',
                'name': '21% Car',
                'price_include': False,
                'amount': 21.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'tax_group_id': f'account.{cid}_tax_group_tva_21',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+82'),
                    }),
                    Command.create({
                        'factor_percent': 50,
                        'repartition_type': 'tax',
                        'tag_ids': tags('+82'),
                    }),
                    Command.create({
                        'factor_percent': 50,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'tag_ids': tags('+59'),
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+85', '-82'),
                    }),
                    Command.create({
                        'factor_percent': 50,
                        'repartition_type': 'tax',
                        'tag_ids': tags('-82', '+85'),
                    }),
                    Command.create({
                        'factor_percent': 50,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'tag_ids': tags('+63'),
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V81-21-EU': {
                'sequence': 1110,
                'description': '21%',
                'name': '21% EU M',
                'price_include': False,
                'amount': 21.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'tax_group_id': f'account.{cid}_tax_group_tva_21',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+81', '+86'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'tag_ids': tags('+59'),
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451055',
                        'tag_ids': tags('-55'),
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('-81', '-86', '+84'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451055',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V81-12-EU': {
                'sequence': 1120,
                'description': '12%',
                'name': '12% EU M',
                'price_include': False,
                'amount': 12.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_12',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+81', '+86'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'tag_ids': tags('+59'),
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451055',
                        'tag_ids': tags('-55'),
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('-81', '-86', '+84'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451055',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V81-06-EU': {
                'sequence': 1130,
                'description': '6%',
                'name': '6% EU M',
                'price_include': False,
                'amount': 6.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_6',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+81', '+86'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'tag_ids': tags('+59'),
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451055',
                        'tag_ids': tags('-55'),
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('-81', '-86', '+84'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451055',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V81-00-EU': {
                'sequence': 1140,
                'description': '0%',
                'name': '0% EU M',
                'price_include': False,
                'amount': 0.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_0',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+81', '+86'),
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
                        'tag_ids': tags('-81', '-86', '+84'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V82-21-EU-S': {
                'sequence': 1210,
                'description': '21%',
                'name': '21% EU S',
                'price_include': False,
                'amount': 21.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_21',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+82', '+88'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'tag_ids': tags('+59'),
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451055',
                        'tag_ids': tags('-55'),
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('-82', '-88', '+84'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451055',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V82-21-EU-G': {
                'sequence': 1220,
                'description': '21%',
                'name': '21% EU G',
                'price_include': False,
                'amount': 21.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_21',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+82', '+86'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'tag_ids': tags('+59'),
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451055',
                        'tag_ids': tags('-55'),
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('-82', '-86', '+84'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451055',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V82-12-EU-S': {
                'sequence': 1230,
                'description': '12%',
                'name': '12% EU S',
                'price_include': False,
                'amount': 12.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_12',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+82', '+88'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'tag_ids': tags('+59'),
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451055',
                        'tag_ids': tags('-55'),
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('-82', '-88', '+84'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451055',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V82-12-EU-G': {
                'sequence': 1240,
                'description': '12%',
                'name': '12% EU G',
                'price_include': False,
                'amount': 12.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_12',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+82', '+86'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'tag_ids': tags('+59'),
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451055',
                        'tag_ids': tags('-55'),
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('-82', '-86', '+84'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451055',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V82-06-EU-S': {
                'sequence': 1250,
                'description': '6%',
                'name': '6% EU S',
                'price_include': False,
                'amount_type': 'percent',
                'amount': 6.0,
                'type_tax_use': 'purchase',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_6',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+82', '+88'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'tag_ids': tags('+59'),
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451055',
                        'tag_ids': tags('-55'),
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('-82', '-88', '+84'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451055',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V82-06-EU-G': {
                'sequence': 1260,
                'description': '6%',
                'name': '6% EU G',
                'price_include': False,
                'amount': 6.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_6',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+82', '+86'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'tag_ids': tags('+59'),
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451055',
                        'tag_ids': tags('-55'),
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('-82', '-86', '+84'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451055',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V82-00-EU-S': {
                'sequence': 1270,
                'description': '0%',
                'name': '0% EU S',
                'price_include': False,
                'amount': 0.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_0',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+82', '+88'),
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
                        'tag_ids': tags('-82', '-88', '+84'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V83-21-EU': {
                'sequence': 1310,
                'description': '21%',
                'name': "21% EU IG",
                'price_include': False,
                'amount': 21.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_21',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+83', '+86'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'tag_ids': tags('+59'),
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451055',
                        'tag_ids': tags('-55'),
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('-83', '-86', '+84'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451055',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V82-00-EU-G': {
                'sequence': 1280,
                'description': '0%',
                'name': '0% EU IG',
                'price_include': False,
                'amount': 0.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_0',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+82', '+86'),
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
                        'tag_ids': tags('-82', '-86', '+84'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V83-12-EU': {
                'sequence': 1320,
                'description': '12%',
                'name': "12% EU IG",
                'price_include': False,
                'amount_type': 'percent',
                'amount': 12.0,
                'type_tax_use': 'purchase',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_12',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+83', '+86'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'tag_ids': tags('+59'),
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451055',
                        'tag_ids': tags('-55'),
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('-83', '-86', '+84'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451055',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V83-06-EU': {
                'sequence': 1330,
                'description': '6%',
                'name': "6% IG",
                'price_include': False,
                'amount_type': 'percent',
                'amount': 6.0,
                'type_tax_use': 'purchase',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_6',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'tag_ids': tags('+83', '+86'),
                        'factor_percent': 100,
                        'repartition_type': 'base',
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'tag_ids': tags('+59'),
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451055',
                        'tag_ids': tags('-55'),
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('-83', '-86', '+84'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451055',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V83-00-EU': {
                'sequence': 1340,
                'description': '0%',
                'name': "0% EU IG",
                'price_include': False,
                'amount': 0.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_0',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+83', '+86'),
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
                        'tag_ids': tags('-83', '-86', '+84'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V81-21-ROW-CC': {
                'sequence': 2110,
                'description': '21%',
                'name': '21% EX M',
                'price_include': False,
                'amount': 21.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'tax_group_id': f'account.{cid}_tax_group_tva_21',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+81', '+87'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'tag_ids': tags('+59'),
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451057',
                        'tag_ids': tags('-57'),
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('-81', '-87', '+85'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451057',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V81-12-ROW-CC': {
                'sequence': 2120,
                'description': '12%',
                'name': '12% EX M',
                'amount': 12.0,
                'price_include': False,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_12',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+81', '+87'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'tag_ids': tags('+59'),
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451057',
                        'tag_ids': tags('-57'),
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('-81', '-87', '+85'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451057',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V81-06-ROW-CC': {
                'sequence': 2130,
                'description': '6%',
                'name': '6% EX M',
                'price_include': False,
                'amount': 6.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_6',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+81', '+87'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'tag_ids': tags('+59'),
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451057',
                        'tag_ids': tags('-57'),
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('-81', '-87', '+85'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451057',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V81-00-ROW-CC': {
                'sequence': 2140,
                'description': '0%',
                'name': '0% EX M',
                'price_include': False,
                'amount': 0.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_0',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+81', '+87'),
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
                        'tag_ids': tags('-81', '-87', '+85'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V82-21-ROW-CC': {
                'sequence': 2210,
                'description': '21%',
                'name': '21% EX S',
                'amount': 21.0,
                'price_include': False,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_21',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+82', '+87'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'tag_ids': tags('+59'),
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451057',
                        'tag_ids': tags('-57'),
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('-82', '-87', '+85'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451057',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V82-12-ROW-CC': {
                'sequence': 2220,
                'description': '12%',
                'name': '12% EX S',
                'price_include': False,
                'amount_type': 'percent',
                'amount': 12.0,
                'type_tax_use': 'purchase',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_12',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+82', '+87'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'tag_ids': tags('+59'),
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451057',
                        'tag_ids': tags('-57'),
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('-82', '-87', '+85'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451057',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V82-06-ROW-CC': {
                'sequence': 2230,
                'description': '6%',
                'name': '6% EX S',
                'price_include': False,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'amount': 6.0,
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_6',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+82', '+87'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'tag_ids': tags('+59'),
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451057',
                        'tag_ids': tags('-57'),
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('-82', '-87', '+85'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451057',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V82-00-ROW-CC': {
                'sequence': 2240,
                'description': '0%',
                'name': '0% EX S',
                'price_include': False,
                'amount': 0.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_0',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+82', '+87'),
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
                        'tag_ids': tags('-82', '-87', '+85'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V83-21-ROW-CC': {
                'sequence': 2310,
                'description': '21%',
                'name': "21% EX IG",
                'amount': 21.0,
                'price_include': False,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_21',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+83', '+87'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'tag_ids': tags('+59'),
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451057',
                        'tag_ids': tags('-57'),
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('-83', '-87', '+85'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451057',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V83-12-ROW-CC': {
                'sequence': 2320,
                'description': '12%',
                'name': "12% EX IG",
                'price_include': False,
                'amount_type': 'percent',
                'amount': 12.0,
                'type_tax_use': 'purchase',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_12',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+83', '+87'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'tag_ids': tags('+59'),
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451057',
                        'tag_ids': tags('-57'),
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('-83', '-87', '+85'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451057',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V83-06-ROW-CC': {
                'sequence': 2330,
                'description': '6%',
                'name': "6% EX IG",
                'price_include': False,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'amount': 6.0,
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_6',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+83', '+87'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'tag_ids': tags('+59'),
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451057',
                        'tag_ids': tags('-57'),
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('-83', '-87', '+85'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451057',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V83-00-ROW-CC': {
                'sequence': 2340,
                'description': '0%',
                'name': "0% EX IG",
                'price_include': False,
                'amount': 0.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_0',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': tags('+83', '+87'),
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
                        'tag_ids': tags('-83', '-87', '+85'),
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            }
        }

    def _get_be_res_company(self, template_code, company):
        company = (company or self.env.company)
        cid = company.id
        return {
            company.get_external_id()[company.id]: {
                'account_fiscal_country_id': 'base.be',
                'account_default_pos_receivable_account_id': f'account.{cid}_a4001',
                'income_currency_exchange_account_id': f'account.{cid}_a754',
                'expense_currency_exchange_account_id': f'account.{cid}_a654',
            }
        }

    def _get_be_fiscal_position(self, template_code, company):
        cid = (company or self.env.company).id
        return {
            f'{cid}_fiscal_position_template_1': {
                'sequence': 1,
                'name': 'Régime National',
                'auto_apply': 1,
                'vat_required': 1,
                'country_id': 'base.be',
            },
            f'{cid}_fiscal_position_template_5': {
                'sequence': 2,
                'name': 'EU privé',
                'auto_apply': 1,
                'country_group_id': 'base.europe',
            },
            f'{cid}_fiscal_position_template_2': {
                'sequence': 4,
                'name': 'Régime Extra-Communautaire',
                'auto_apply': 1,
            },
            f'{cid}_fiscal_position_template_3': {
                'sequence': 3,
                'name': 'Régime Intra-Communautaire',
                'auto_apply': 1,
                'vat_required': 1,
                'country_group_id': 'base.europe',
            },
            f'{cid}_fiscal_position_template_4': {
                'name': 'Régime Cocontractant',
                'sequence': 5,
            }
        }

    def _get_be_reconcile_model(self, template_code, company):
        cid = (company or self.env.company).id
        return {
            f'{cid}_escompte_template': {
                'name': 'Escompte',
            },
            f'{cid}_frais_bancaires_htva_template': {
                'name': 'Frais bancaires HTVA',
            },
            f'{cid}_frais_bancaires_tva21_template': {
                'name': 'Frais bancaires TVA21',
            },
            f'{cid}_virements_internes_template': {
                'name': 'Virements internes',
                'to_check': False,
            },
            f'{cid}_compte_attente_template': {
                'name': 'Compte Attente',
                'to_check': True,
            }
        }

    def _get_be_reconcile_model_line(self, template_code, company):
        cid = (company or self.env.company).id
        return {
            f'{cid}_escompte_line_template': {
                'model_id': 'l10n_be.escompte_template',
                'account_id': 'a653',
                'amount_type': 'percentage',
                'amount_string': '100',
                'label': 'Escompte accordé',
            },
            f'{cid}_frais_bancaires_htva_line_template': {
                'model_id': 'l10n_be.frais_bancaires_htva_template',
                'account_id': 'a6560',
                'amount_type': 'percentage',
                'amount_string': '100',
                'label': 'Frais bancaires HTVA',
            },
            f'{cid}_frais_bancaires_tva21_line_template': {
                'model_id': 'l10n_be.frais_bancaires_tva21_template',
                'account_id': 'a6560',
                'amount_type': 'percentage',
                'tax_ids': [
                    Command.set([
                        'l10n_be.attn_TVA-21-inclus-dans-prix',
                    ]),
                ],
                'amount_string': '100',
                'label': 'Frais bancaires TVA21',
            },
            f'{cid}_virements_internes_line_template': {
                'model_id': 'l10n_be.virements_internes_template',
                'account_id': None,
                'amount_type': 'percentage',
                'amount_string': '100',
                'label': 'Virements internes',
            },
            f'{cid}_compte_attente_line_template': {
                'model_id': 'l10n_be.compte_attente_template',
                'account_id': 'a499',
                'amount_type': 'percentage',
                'amount_string': '100',
                'label': None,
            }
        }

    def _get_be_fiscal_position_tax(self, template_code, company):
        cid = (company or self.env.company).id
        return {
            f'{cid}_afpttn_intracom_1': {
                'position_id': f'account.{cid}_fiscal_position_template_3',
                'tax_src_id': f'account.{cid}_attn_VAT-OUT-00-S',
                'tax_dest_id': f'account.{cid}_attn_VAT-OUT-00-EU-S',
            },
            f'{cid}_afpttn_intracom_2': {
                'position_id': f'account.{cid}_fiscal_position_template_3',
                'tax_src_id': f'account.{cid}_attn_VAT-OUT-00-L',
                'tax_dest_id': f'account.{cid}_attn_VAT-OUT-00-EU-L',
            },
            f'{cid}_afpttn_intracom_3': {
                'position_id': f'account.{cid}_fiscal_position_template_3',
                'tax_src_id': f'account.{cid}_attn_VAT-OUT-06-S',
                'tax_dest_id': f'account.{cid}_attn_VAT-OUT-00-EU-S',
            },
            f'{cid}_afpttn_intracom_4': {
                'position_id': f'account.{cid}_fiscal_position_template_3',
                'tax_src_id': f'account.{cid}_attn_VAT-OUT-06-L',
                'tax_dest_id': f'account.{cid}_attn_VAT-OUT-00-EU-L',
            },
            f'{cid}_afpttn_intracom_5': {
                'position_id': f'account.{cid}_fiscal_position_template_3',
                'tax_src_id': f'account.{cid}_attn_VAT-OUT-12-S',
                'tax_dest_id': f'account.{cid}_attn_VAT-OUT-00-EU-S',
            },
            f'{cid}_afpttn_intracom_6': {
                'position_id': f'account.{cid}_fiscal_position_template_3',
                'tax_src_id': f'account.{cid}_attn_VAT-OUT-12-L',
                'tax_dest_id': f'account.{cid}_attn_VAT-OUT-00-EU-L',
            },
            f'{cid}_afpttn_intracom_7': {
                'position_id': f'account.{cid}_fiscal_position_template_3',
                'tax_src_id': f'account.{cid}_attn_VAT-OUT-21-S',
                'tax_dest_id': f'account.{cid}_attn_VAT-OUT-00-EU-S',
            },
            f'{cid}_afpttn_intracom_8': {
                'position_id': f'account.{cid}_fiscal_position_template_3',
                'tax_src_id': f'account.{cid}_attn_VAT-OUT-21-L',
                'tax_dest_id': f'account.{cid}_attn_VAT-OUT-00-EU-L',
            },
            f'{cid}_afpttn_intracom_9': {
                'position_id': f'account.{cid}_fiscal_position_template_3',
                'tax_src_id': f'account.{cid}_attn_VAT-IN-V81-00',
                'tax_dest_id': f'account.{cid}_attn_VAT-IN-V81-00-EU',
            },
            f'{cid}_afpttn_intracom_10': {
                'position_id': f'account.{cid}_fiscal_position_template_3',
                'tax_src_id': f'account.{cid}_attn_VAT-IN-V81-06',
                'tax_dest_id': f'account.{cid}_attn_VAT-IN-V81-06-EU',
            },
            f'{cid}_afpttn_intracom_11': {
                'position_id': f'account.{cid}_fiscal_position_template_3',
                'tax_src_id': f'account.{cid}_attn_VAT-IN-V81-12',
                'tax_dest_id': f'account.{cid}_attn_VAT-IN-V81-12-EU',
            },
            f'{cid}_afpttn_intracom_12': {
                'position_id': f'account.{cid}_fiscal_position_template_3',
                'tax_src_id': f'account.{cid}_attn_VAT-IN-V81-21',
                'tax_dest_id': f'account.{cid}_attn_VAT-IN-V81-21-EU',
            },
            f'{cid}_afpttn_intracom_13': {
                'position_id': f'account.{cid}_fiscal_position_template_3',
                'tax_src_id': f'account.{cid}_attn_VAT-IN-V82-00-S',
                'tax_dest_id': f'account.{cid}_attn_VAT-IN-V82-00-EU-S',
            },
            f'{cid}_afpttn_intracom_14': {
                'position_id': f'account.{cid}_fiscal_position_template_3',
                'tax_src_id': f'account.{cid}_attn_VAT-IN-V82-00-G',
                'tax_dest_id': f'account.{cid}_attn_VAT-IN-V82-00-EU-G',
            },
            f'{cid}_afpttn_intracom_15': {
                'position_id': f'account.{cid}_fiscal_position_template_3',
                'tax_src_id': f'account.{cid}_attn_VAT-IN-V82-06-S',
                'tax_dest_id': f'account.{cid}_attn_VAT-IN-V82-06-EU-S',
            },
            f'{cid}_afpttn_intracom_16': {
                'position_id': f'account.{cid}_fiscal_position_template_3',
                'tax_src_id': f'account.{cid}_attn_VAT-IN-V82-06-G',
                'tax_dest_id': f'account.{cid}_attn_VAT-IN-V82-06-EU-G',
            },
            f'{cid}_afpttn_intracom_17': {
                'position_id': f'account.{cid}_fiscal_position_template_3',
                'tax_src_id': f'account.{cid}_attn_VAT-IN-V82-12-S',
                'tax_dest_id': f'account.{cid}_attn_VAT-IN-V82-12-EU-S',
            },
            f'{cid}_afpttn_intracom_18': {
                'position_id': f'account.{cid}_fiscal_position_template_3',
                'tax_src_id': f'account.{cid}_attn_VAT-IN-V82-12-G',
                'tax_dest_id': f'account.{cid}_attn_VAT-IN-V82-12-EU-G',
            },
            f'{cid}_afpttn_intracom_19': {
                'position_id': f'account.{cid}_fiscal_position_template_3',
                'tax_src_id': f'account.{cid}_attn_VAT-IN-V82-21-S',
                'tax_dest_id': f'account.{cid}_attn_VAT-IN-V82-21-EU-S',
            },
            f'{cid}_afpttn_intracom_20': {
                'position_id': f'account.{cid}_fiscal_position_template_3',
                'tax_src_id': f'account.{cid}_attn_VAT-IN-V82-21-G',
                'tax_dest_id': f'account.{cid}_attn_VAT-IN-V82-21-EU-G',
            },
            f'{cid}_afpttn_intracom_21': {
                'position_id': f'account.{cid}_fiscal_position_template_3',
                'tax_src_id': f'account.{cid}_attn_VAT-IN-V83-00',
                'tax_dest_id': f'account.{cid}_attn_VAT-IN-V83-00-EU',
            },
            f'{cid}_afpttn_intracom_22': {
                'position_id': f'account.{cid}_fiscal_position_template_3',
                'tax_src_id': f'account.{cid}_attn_VAT-IN-V83-06',
                'tax_dest_id': f'account.{cid}_attn_VAT-IN-V83-06-EU',
            },
            f'{cid}_afpttn_intracom_23': {
                'position_id': f'account.{cid}_fiscal_position_template_3',
                'tax_src_id': f'account.{cid}_attn_VAT-IN-V83-12',
                'tax_dest_id': f'account.{cid}_attn_VAT-IN-V83-12-EU',
            },
            f'{cid}_afpttn_intracom_24': {
                'position_id': f'account.{cid}_fiscal_position_template_3',
                'tax_src_id': f'account.{cid}_attn_VAT-IN-V83-21',
                'tax_dest_id': f'account.{cid}_attn_VAT-IN-V83-21-EU',
            },
            f'{cid}_afpttn_extracom_1': {
                'position_id': f'account.{cid}_fiscal_position_template_2',
                'tax_src_id': f'account.{cid}_attn_VAT-OUT-00-S',
                'tax_dest_id': f'account.{cid}_attn_VAT-OUT-00-ROW',
            },
            f'{cid}_afpttn_extracom_2': {
                'position_id': f'account.{cid}_fiscal_position_template_2',
                'tax_src_id': f'account.{cid}_attn_VAT-OUT-00-L',
                'tax_dest_id': f'account.{cid}_attn_VAT-OUT-00-ROW',
            },
            f'{cid}_afpttn_extracom_3': {
                'position_id': f'account.{cid}_fiscal_position_template_2',
                'tax_src_id': f'account.{cid}_attn_VAT-OUT-06-S',
                'tax_dest_id': f'account.{cid}_attn_VAT-OUT-00-ROW',
            },
            f'{cid}_afpttn_extracom_4': {
                'position_id': f'account.{cid}_fiscal_position_template_2',
                'tax_src_id': f'account.{cid}_attn_VAT-OUT-06-L',
                'tax_dest_id': f'account.{cid}_attn_VAT-OUT-00-ROW',
            },
            f'{cid}_afpttn_extracom_5': {
                'position_id': f'account.{cid}_fiscal_position_template_2',
                'tax_src_id': f'account.{cid}_attn_VAT-OUT-12-S',
                'tax_dest_id': f'account.{cid}_attn_VAT-OUT-00-ROW',
            },
            f'{cid}_afpttn_extracom_6': {
                'position_id': f'account.{cid}_fiscal_position_template_2',
                'tax_src_id': f'account.{cid}_attn_VAT-OUT-12-L',
                'tax_dest_id': f'account.{cid}_attn_VAT-OUT-00-ROW',
            },
            f'{cid}_afpttn_extracom_7': {
                'position_id': f'account.{cid}_fiscal_position_template_2',
                'tax_src_id': f'account.{cid}_attn_VAT-OUT-21-S',
                'tax_dest_id': f'account.{cid}_attn_VAT-OUT-00-ROW',
            },
            f'{cid}_afpttn_extracom_8': {
                'position_id': f'account.{cid}_fiscal_position_template_2',
                'tax_src_id': f'account.{cid}_attn_VAT-OUT-21-L',
                'tax_dest_id': f'account.{cid}_attn_VAT-OUT-00-ROW',
            },
            f'{cid}_afpttn_extracom_9': {
                'position_id': f'account.{cid}_fiscal_position_template_2',
                'tax_src_id': f'account.{cid}_attn_VAT-IN-V81-06',
                'tax_dest_id': f'account.{cid}_attn_VAT-IN-V81-06-ROW-CC',
            },
            f'{cid}_afpttn_extracom_10': {
                'position_id': f'account.{cid}_fiscal_position_template_2',
                'tax_src_id': f'account.{cid}_attn_VAT-IN-V81-12',
                'tax_dest_id': f'account.{cid}_attn_VAT-IN-V81-12-ROW-CC',
            },
            f'{cid}_afpttn_extracom_11': {
                'position_id': f'account.{cid}_fiscal_position_template_2',
                'tax_src_id': f'account.{cid}_attn_VAT-IN-V81-21',
                'tax_dest_id': f'account.{cid}_attn_VAT-IN-V81-21-ROW-CC',
            },
            f'{cid}_afpttn_extracom_12': {
                'position_id': f'account.{cid}_fiscal_position_template_2',
                'tax_src_id': f'account.{cid}_attn_VAT-IN-V82-06-S',
                'tax_dest_id': f'account.{cid}_attn_VAT-IN-V82-06-ROW-CC',
            },
            f'{cid}_afpttn_extracom_13': {
                'position_id': f'account.{cid}_fiscal_position_template_2',
                'tax_src_id': f'account.{cid}_attn_VAT-IN-V82-06-G',
                'tax_dest_id': f'account.{cid}_attn_VAT-IN-V82-06-ROW-CC',
            },
            f'{cid}_afpttn_extracom_14': {
                'position_id': f'account.{cid}_fiscal_position_template_2',
                'tax_src_id': f'account.{cid}_attn_VAT-IN-V82-12-S',
                'tax_dest_id': f'account.{cid}_attn_VAT-IN-V82-12-ROW-CC',
            },
            f'{cid}_afpttn_extracom_15': {
                'position_id': f'account.{cid}_fiscal_position_template_2',
                'tax_src_id': f'account.{cid}_attn_VAT-IN-V82-12-G',
                'tax_dest_id': f'account.{cid}_attn_VAT-IN-V82-12-ROW-CC',
            },
            f'{cid}_afpttn_extracom_16': {
                'position_id': f'account.{cid}_fiscal_position_template_2',
                'tax_src_id': f'account.{cid}_attn_VAT-IN-V82-21-S',
                'tax_dest_id': f'account.{cid}_attn_VAT-IN-V82-21-ROW-CC',
            },
            f'{cid}_afpttn_extracom_17': {
                'position_id': f'account.{cid}_fiscal_position_template_2',
                'tax_src_id': f'account.{cid}_attn_VAT-IN-V82-21-G',
                'tax_dest_id': f'account.{cid}_attn_VAT-IN-V82-21-ROW-CC',
            },
            f'{cid}_afpttn_extracom_18': {
                'position_id': f'account.{cid}_fiscal_position_template_2',
                'tax_src_id': f'account.{cid}_attn_VAT-IN-V83-06',
                'tax_dest_id': f'account.{cid}_attn_VAT-IN-V83-06-ROW-CC',
            },
            f'{cid}_afpttn_extracom_19': {
                'position_id': f'account.{cid}_fiscal_position_template_2',
                'tax_src_id': f'account.{cid}_attn_VAT-IN-V83-12',
                'tax_dest_id': f'account.{cid}_attn_VAT-IN-V83-12-ROW-CC',
            },
            f'{cid}_afpttn_extracom_20': {
                'position_id': f'account.{cid}_fiscal_position_template_2',
                'tax_src_id': f'account.{cid}_attn_VAT-IN-V83-21',
                'tax_dest_id': f'account.{cid}_attn_VAT-IN-V83-21-ROW-CC',
            },
            f'{cid}_afpttn_cocontractant_1': {
                'position_id': f'account.{cid}_fiscal_position_template_4',
                'tax_src_id': f'account.{cid}_attn_VAT-OUT-00-S',
                'tax_dest_id': f'account.{cid}_attn_VAT-OUT-00-CC',
            },
            f'{cid}_afpttn_cocontractant_2': {
                'position_id': f'account.{cid}_fiscal_position_template_4',
                'tax_src_id': f'account.{cid}_attn_VAT-OUT-00-L',
                'tax_dest_id': f'account.{cid}_attn_VAT-OUT-00-CC',
            },
            f'{cid}_afpttn_cocontractant_3': {
                'position_id': f'account.{cid}_fiscal_position_template_4',
                'tax_src_id': f'account.{cid}_attn_VAT-OUT-06-S',
                'tax_dest_id': f'account.{cid}_attn_VAT-OUT-00-CC',
            },
            f'{cid}_afpttn_cocontractant_4': {
                'position_id': f'account.{cid}_fiscal_position_template_4',
                'tax_src_id': f'account.{cid}_attn_VAT-OUT-06-L',
                'tax_dest_id': f'account.{cid}_attn_VAT-OUT-00-CC',
            },
            f'{cid}_afpttn_cocontractant_5': {
                'position_id': f'account.{cid}_fiscal_position_template_4',
                'tax_src_id': f'account.{cid}_attn_VAT-OUT-12-S',
                'tax_dest_id': f'account.{cid}_attn_VAT-OUT-00-CC',
            },
            f'{cid}_afpttn_cocontractant_6': {
                'position_id': f'account.{cid}_fiscal_position_template_4',
                'tax_src_id': f'account.{cid}_attn_VAT-OUT-12-L',
                'tax_dest_id': f'account.{cid}_attn_VAT-OUT-00-CC',
            },
            f'{cid}_afpttn_cocontractant_7': {
                'position_id': f'account.{cid}_fiscal_position_template_4',
                'tax_src_id': f'account.{cid}_attn_VAT-OUT-21-S',
                'tax_dest_id': f'account.{cid}_attn_VAT-OUT-00-CC',
            },
            f'{cid}_afpttn_cocontractant_8': {
                'position_id': f'account.{cid}_fiscal_position_template_4',
                'tax_src_id': f'account.{cid}_attn_VAT-OUT-21-L',
                'tax_dest_id': f'account.{cid}_attn_VAT-OUT-00-CC',
            },
            f'{cid}_afpttn_cocontractant_9': {
                'position_id': f'account.{cid}_fiscal_position_template_4',
                'tax_src_id': f'account.{cid}_attn_VAT-IN-V81-06',
                'tax_dest_id': f'account.{cid}_attn_VAT-IN-V81-06-CC',
            },
            f'{cid}_afpttn_cocontractant_10': {
                'position_id': f'account.{cid}_fiscal_position_template_4',
                'tax_src_id': f'account.{cid}_attn_VAT-IN-V81-12',
                'tax_dest_id': f'account.{cid}_attn_VAT-IN-V81-12-CC',
            },
            f'{cid}_afpttn_cocontractant_11': {
                'position_id': f'account.{cid}_fiscal_position_template_4',
                'tax_src_id': f'account.{cid}_attn_VAT-IN-V81-21',
                'tax_dest_id': f'account.{cid}_attn_VAT-IN-V81-21-CC',
            },
            f'{cid}_afpttn_cocontractant_12': {
                'position_id': f'account.{cid}_fiscal_position_template_4',
                'tax_src_id': f'account.{cid}_attn_VAT-IN-V82-06-S',
                'tax_dest_id': f'account.{cid}_attn_VAT-IN-V82-06-CC',
            },
            f'{cid}_afpttn_cocontractant_13': {
                'position_id': f'account.{cid}_fiscal_position_template_4',
                'tax_src_id': f'account.{cid}_attn_VAT-IN-V82-06-G',
                'tax_dest_id': f'account.{cid}_attn_VAT-IN-V82-06-CC',
            },
            f'{cid}_afpttn_cocontractant_14': {
                'position_id': f'account.{cid}_fiscal_position_template_4',
                'tax_src_id': f'account.{cid}_attn_VAT-IN-V82-12-S',
                'tax_dest_id': f'account.{cid}_attn_VAT-IN-V82-12-CC',
            },
            f'{cid}_afpttn_cocontractant_15': {
                'position_id': f'account.{cid}_fiscal_position_template_4',
                'tax_src_id': f'account.{cid}_attn_VAT-IN-V82-12-G',
                'tax_dest_id': f'account.{cid}_attn_VAT-IN-V82-12-CC',
            },
            f'{cid}_afpttn_cocontractant_16': {
                'position_id': f'account.{cid}_fiscal_position_template_4',
                'tax_src_id': f'account.{cid}_attn_VAT-IN-V82-21-S',
                'tax_dest_id': f'account.{cid}_attn_VAT-IN-V82-21-CC',
            },
            f'{cid}_afpttn_cocontractant_17': {
                'position_id': f'account.{cid}_fiscal_position_template_4',
                'tax_src_id': f'account.{cid}_attn_VAT-IN-V82-21-G',
                'tax_dest_id': f'account.{cid}_attn_VAT-IN-V82-21-CC',
            },
            f'{cid}_afpttn_cocontractant_18': {
                'position_id': f'account.{cid}_fiscal_position_template_4',
                'tax_src_id': f'account.{cid}_attn_VAT-IN-V83-06',
                'tax_dest_id': f'account.{cid}_attn_VAT-IN-V83-06-CC',
            },
            f'{cid}_afpttn_cocontractant_19': {
                'position_id': f'account.{cid}_fiscal_position_template_4',
                'tax_src_id': f'account.{cid}_attn_VAT-IN-V83-12',
                'tax_dest_id': f'account.{cid}_attn_VAT-IN-V83-12-CC',
            },
            f'{cid}_afpttn_cocontractant_20': {
                'position_id': f'account.{cid}_fiscal_position_template_4',
                'tax_src_id': f'account.{cid}_attn_VAT-IN-V83-21',
                'tax_dest_id': f'account.{cid}_attn_VAT-IN-V83-21-CC',
            }
        }
