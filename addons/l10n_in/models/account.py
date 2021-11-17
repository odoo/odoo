# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo import tools


class AccountJournal(models.Model):
    _inherit = "account.journal"

    # Use for filter import and export type.
    l10n_in_gstin_partner_id = fields.Many2one('res.partner', string="GSTIN Unit", ondelete="restrict", help="GSTIN related to this journal. If empty then consider as company GSTIN.")

    def name_get(self):
        """
            Add GSTIN number in name as suffix so user can easily find the right journal.
            Used super to ensure nothing is missed.
        """
        result = super().name_get()
        result_dict = dict(result)
        indian_journals = self.filtered(lambda j: j.company_id.account_fiscal_country_id.code == 'IN' and
            j.l10n_in_gstin_partner_id and j.l10n_in_gstin_partner_id.vat)
        for journal in indian_journals:
            name = result_dict[journal.id]
            name += "- %s" % (journal.l10n_in_gstin_partner_id.vat)
            result_dict[journal.id] = name
        return list(result_dict.items())


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

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

    @api.model
    def _get_generation_dict_from_base_line(self, line_vals, tax_vals):
        # EXTENDS account
        # Group taxes also by product.
        res = super()._get_generation_dict_from_base_line(line_vals, tax_vals)
        record = line_vals['record']
        if isinstance(record, models.Model)\
                and record._name == 'account.move.line'\
                and record.company_id.account_fiscal_country_id.code == 'IN':
            res['product_id'] = record.product_id.id
            res['product_uom_id'] = record.product_uom_id.id
        return res

    @api.model
    def _get_generation_dict_from_tax_line(self, line_vals):
        # EXTENDS account
        # Group taxes also by product.
        res = super()._get_generation_dict_from_tax_line(line_vals)
        record = line_vals['record']
        if isinstance(record, models.Model)\
                and record._name == 'account.move.line'\
                and record.company_id.account_fiscal_country_id.code == 'IN':
            res['product_id'] = record.product_id.id
            res['product_uom_id'] = record.product_uom_id.id
        return res
