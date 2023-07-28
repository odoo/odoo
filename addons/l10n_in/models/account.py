# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo import tools


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
