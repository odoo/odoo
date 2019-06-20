# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.depends('amount_total')
    def _compute_amount_total_words(self):
        for invoice in self:
            invoice.amount_total_words = invoice.currency_id.amount_to_text(invoice.amount_total)

    amount_total_words = fields.Char("Total (In Words)", compute="_compute_amount_total_words")
    # Use for invisible fields in form views.
    l10n_in_import_export = fields.Boolean(related='journal_id.l10n_in_import_export', readonly=True)
    # For Export invoice this data is need in GSTR report
    l10n_in_export_type = fields.Selection([
        ('regular', 'Regular'), ('deemed', 'Deemed'),
        ('sale_from_bonded_wh', 'Sale from Bonded WH'),
        ('export_with_igst', 'Export with IGST'),
        ('sez_with_igst', 'SEZ with IGST payment'),
        ('sez_without_igst', 'SEZ without IGST payment')],
        string='Export Type', default='regular', required=True)
    l10n_in_shipping_bill_number = fields.Char('Shipping bill number', readonly=True, states={'draft': [('readonly', False)]})
    l10n_in_shipping_bill_date = fields.Date('Shipping bill date', readonly=True, states={'draft': [('readonly', False)]})
    l10n_in_shipping_port_code_id = fields.Many2one('l10n_in.port.code', 'Shipping port code', states={'draft': [('readonly', False)]})
    l10n_in_reseller_partner_id = fields.Many2one('res.partner', 'Reseller', domain=[('vat', '!=', False)], help="Only Registered Reseller", readonly=True, states={'draft': [('readonly', False)]})
    l10n_in_partner_vat = fields.Char(related="partner_id.vat", readonly=True)
    l10n_in_unit_id = fields.Many2one('res.partner', string="Operating Unit",
        ondelete="restrict", readonly=True, states={'draft': [('readonly', False)]}, default=lambda self: self.env.user._get_default_unit())

    @api.onchange('journal_id')
    def _onchange_journal(self):
        res = super(AccountMove, self)._onchange_journal()
        self.l10n_in_unit_id = self.journal_id.l10n_in_unit_id or self.env.user._get_default_unit()
        return res

    @api.model
    def _get_tax_grouping_key_from_tax_line(self, tax_line):
        # OVERRIDE to group taxes also by product.
        res = super()._get_tax_grouping_key_from_tax_line(tax_line)
        res['product_id'] = tax_line.product_id.id
        return res

    @api.model
    def _get_tax_grouping_key_from_base_line(self, base_line, tax_vals):
        # OVERRIDE to group taxes also by product.
        res = super()._get_tax_grouping_key_from_base_line(base_line, tax_vals)
        res.update({
            'product_id': base_line.product_id.id,
            'product_uom_id': base_line.product_uom_id.id,
            'quantity': base_line.quantity,
        })
        return res

    @api.model
    def create(self, vals):
        if not vals.get('l10n_in_unit_id'):
            if vals.get('journal_id'):
                journal_id = self.env['account.journal'].browse(vals['journal_id'])
                vals['l10n_in_unit_id'] = journal_id.l10n_in_unit_id and journal_id.l10n_in_unit_id.id or journal_id.company_id.partner_id.id
            else:
                vals['l10n_in_unit_id'] = self.env.user.company_id.partner_id.id
        return super(AccountMove, self).create(vals)

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    l10n_in_unit_id = fields.Many2one(related='move_id.l10n_in_unit_id', store=True, readonly=True)

    @api.model
    def _query_get(self, domain=None):
        context = dict(self._context or {})
        domain = domain or []
        if context.get('l10n_in_unit_id'):
            domain += [('move_id.l10n_in_unit_id', '=', context['l10n_in_unit_id'])]

        if context.get('l10n_in_unit_ids'):
            domain += [('move_id.l10n_in_unit_id', 'in', context['l10n_in_unit_ids'])]
        return super(AccountMoveLine, self)._query_get(domain=domain)
