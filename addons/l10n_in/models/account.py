# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AccountJournal(models.Model):
    _inherit = "account.journal"

    # Use for filter import and export type.
    l10n_in_import_export = fields.Boolean("Import/Export", help="Tick this if this journal is use for Import/Export Under Indian GST.")
    l10n_in_gstin_partner_id = fields.Many2one('res.partner', string="GSTIN", ondelete="restrict", help="GSTIN related to this journal. If empty then consider as company GSTIN.")

    def name_get(self):
        """
            Add GSTIN number in name as suffix so user can easily find the right journal.
            Used super to ensure nothing is missed.
        """
        result = super().name_get()
        result_dict = dict(result)
        indian_journals = self.filtered(lambda j: j.company_id.country_id.code == 'IN' and
            j.l10n_in_gstin_partner_id and j.l10n_in_gstin_partner_id.vat)
        for journal in indian_journals:
            name = result_dict[journal.id]
            name += "- %s" % (journal.l10n_in_gstin_partner_id.vat)
            result_dict[journal.id] = name
        return list(result_dict.items())


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.depends('move_id.line_ids', 'move_id.line_ids.tax_line_id', 'move_id.line_ids.debit', 'move_id.line_ids.credit')
    def _compute_tax_base_amount(self):
        aml = self.filtered(lambda l: l.company_id.country_id.code == 'IN' and l.tax_line_id  and l.product_id)
        for move_line in aml:
            base_lines = move_line.move_id.line_ids.filtered(lambda line: move_line.tax_line_id in line.tax_ids and move_line.product_id == line.product_id)
            move_line.tax_base_amount = abs(sum(base_lines.mapped('balance')))
        remaining_aml = self - aml
        if remaining_aml:
            return super(AccountMoveLine, remaining_aml)._compute_tax_base_amount()


class AccountTax(models.Model):
    _inherit = 'account.tax'

    l10n_in_reverse_charge = fields.Boolean("Reverse charge", help="Tick this if this tax is reverse charge. Only for Indian accounting")

    def get_grouping_key(self, invoice_tax_val):
        """ Returns a string that will be used to group account.invoice.tax sharing the same properties"""
        # DEAD CODE: REMOVE IN MASTER
        key = super(AccountTax, self).get_grouping_key(invoice_tax_val)
        if self.company_id.country_id.code == 'IN':
            key += "-%s-%s"% (invoice_tax_val.get('l10n_in_product_id', False),
                invoice_tax_val.get('l10n_in_uom_id', False))
        return key

    @api.model
    def _get_tax_grouping_key_from_tax_line(self, tax_line_vals):
        # OVERRIDE to group taxes also by product.
        res = super()._get_tax_grouping_key_from_tax_line(tax_line_vals)
        if 'company_id' in tax_line_vals and 'product_id' in tax_line_vals:
            company = self.env['res.company'].browse(tax_line_vals['company_id'])
            if company.country_id.code == 'IN':
                res['product_id'] = tax_line_vals['product_id']
        return res

    @api.model
    def _get_tax_grouping_key_from_base_line(self, base_line_vals, tax_vals):
        # OVERRIDE to group taxes also by product.
        res = super()._get_tax_grouping_key_from_base_line(base_line_vals, tax_vals)
        if 'company_id' in base_line_vals and 'product_id' in base_line_vals:
            company = self.env['res.company'].browse(base_line_vals['company_id'])
            if company.country_id.code == 'IN':
                res['product_id'] = base_line_vals['product_id']
        return res
