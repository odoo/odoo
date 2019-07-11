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

    @api.multi
    def _invoice_line_tax_values(self):
        #This method for tax value per invoice line in PDF
        self.ensure_one()
        tax_datas = {}
        for line in self.invoice_line_ids:
            price_unit = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            tax_lines = line.tax_ids.compute_all(price_unit, line.move_id.currency_id, line.quantity, line.product_id, line.partner_id, self.type in ('in_refund', 'out_refund'))['taxes']
            for tax_line in tax_lines:
                tax_line['tax_report_line_ids'] = self.env['account.tax.repartition.line'].browse(tax_line['tax_repartition_line_id']).mapped('tag_ids.tax_report_line_ids')
            tax_datas[line.id] = tax_lines
        return tax_datas
