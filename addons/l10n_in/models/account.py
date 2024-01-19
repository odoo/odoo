# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo import tools
from odoo.tools import frozendict


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    l10n_in_hsn_code = fields.Char(string="HSN/SAC Code", compute="_compute_l10n_in_hsn_code", store=True, readonly=False, copy=False)

    @api.depends('product_id')
    def _compute_l10n_in_hsn_code(self):
        indian_lines = self.filtered(lambda line: line.company_id.account_fiscal_country_id.code == 'IN')
        (self - indian_lines).l10n_in_hsn_code = False
        for line in indian_lines:
            if line.product_id:
                line.l10n_in_hsn_code = line.product_id.l10n_in_hsn_code

    def init(self):
        tools.create_index(self._cr, 'account_move_line_move_product_index', self._table, ['move_id', 'product_id'])

    @api.depends('move_id.line_ids', 'move_id.line_ids.tax_line_id', 'move_id.line_ids.debit', 'move_id.line_ids.credit')
    def _compute_tax_base_amount(self):
        aml = self.filtered(lambda l: l.company_id.account_fiscal_country_id.code == 'IN' and l.tax_line_id  and l.product_id)
        for move_line in aml:
            base_lines = move_line.move_id.line_ids.filtered(lambda line: move_line.tax_line_id in line.tax_ids and move_line.product_id == line.product_id)
            move_line.tax_base_amount = abs(sum(base_lines.mapped('balance')))
        remaining_aml = self - aml
        if remaining_aml:
            return super(AccountMoveLine, remaining_aml)._compute_tax_base_amount()


class AccountTax(models.Model):
    _inherit = 'account.tax'

    l10n_in_reverse_charge = fields.Boolean("Reverse charge", help="Tick this if this tax is reverse charge. Only for Indian accounting")

    def _prepare_dict_for_taxes_computation(self):
        # EXTENDS 'account'
        tax_values = super()._prepare_dict_for_taxes_computation()

        if self.country_code == 'IN':
            l10n_in_tax_type = None
            tags = self.invoice_repartition_line_ids.tag_ids
            if self.env.ref('l10n_in.tax_tag_igst') in tags:
                l10n_in_tax_type = 'igst'
            elif self.env.ref('l10n_in.tax_tag_cgst') in tags:
                l10n_in_tax_type = 'cgst'
            elif self.env.ref('l10n_in.tax_tag_sgst') in tags:
                l10n_in_tax_type = 'sgst'
            elif self.env.ref('l10n_in.tax_tag_cess') in tags:
                l10n_in_tax_type = 'cess'
            tax_values['_l10n_in_tax_type'] = l10n_in_tax_type

        return tax_values

    # -------------------------------------------------------------------------
    # HELPERS IN BOTH PYTHON/JAVASCRIPT (hsn_summary.js / account_tax.py)

    # HSN SUMMARY
    # -------------------------------------------------------------------------

    @api.model
    def _l10n_in_get_hsn_summary_table(self, base_lines, display_uom):
        results_map = {}
        l10n_in_tax_types = set()
        for base_line in base_lines:
            l10n_in_hsn_code = base_line['l10n_in_hsn_code']
            if not l10n_in_hsn_code:
                continue

            price_unit = base_line['price_unit']
            quantity = base_line['quantity']
            uom = base_line['uom'] or {}
            tax_values_list = base_line['tax_values_list']

            # Compute the taxes.
            evaluation_context = self.env['account.tax']._eval_taxes_computation_prepare_context(
                price_unit,
                quantity,
                rounding_method='round_per_line',
                precision_rounding=0.01,
            )
            taxes_computation = self.env['account.tax']._eval_taxes_computation(
                self.env['account.tax']._prepare_taxes_computation(tax_values_list),
                evaluation_context,
            )

            # Rate.
            rate = sum(
                tax_values['amount']
                for tax_values in taxes_computation['tax_values_list']
                if tax_values['_l10n_in_tax_type'] in ('igst', 'cgst', 'sgst')
            )

            key = frozendict({
                'l10n_in_hsn_code': l10n_in_hsn_code,
                'rate': rate,
                'uom_name': uom.get('name'),
            })

            if key in results_map:
                values = results_map[key]
                values['quantity'] += quantity
                values['amount_untaxed'] += taxes_computation['total_excluded']
            else:
                results_map[key] = {
                    **key,
                    'quantity': quantity,
                    'amount_untaxed': taxes_computation['total_excluded'],
                    'tax_amounts': {
                        'igst': 0.0,
                        'cgst': 0.0,
                        'sgst': 0.0,
                        'cess': 0.0,
                    },
                }

            for tax_values in taxes_computation['tax_values_list']:
                l10n_in_tax_type = tax_values['_l10n_in_tax_type']
                if l10n_in_tax_type:
                    results_map[key]['tax_amounts'][l10n_in_tax_type] += tax_values['tax_amount_factorized']
                    l10n_in_tax_types.add(l10n_in_tax_type)

        items = [
            {
                'l10n_in_hsn_code': value['l10n_in_hsn_code'],
                'uom_name': value['uom_name'],
                'rate': value['rate'],
                'quantity': value['quantity'],
                'amount_untaxed': value['amount_untaxed'],
                'tax_amount_igst': value['tax_amounts']['igst'],
                'tax_amount_cgst': value['tax_amounts']['cgst'],
                'tax_amount_sgst': value['tax_amounts']['sgst'],
                'tax_amount_cess': value['tax_amounts']['cess'],
            }
            for value in results_map.values()
        ]
        return {
            'has_igst': 'igst' in l10n_in_tax_types,
            'has_gst': bool({'cgst', 'sgst'} & l10n_in_tax_types),
            'has_cess': 'cess' in l10n_in_tax_types,
            'nb_columns': 5 + len(l10n_in_tax_types),
            'display_uom': display_uom,
            'items': items,
        }
