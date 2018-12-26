# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api, fields


class AccountInvoice(models.Model):
    _inherit = 'account.move'

    l10n_it_ddt_ids = fields.Many2many('stock.picking', compute="_compute_ddt_ids")

    def _get_ddt_values(self):
        line_count = 0
        invoice_line_pickings = {}
        for line in self.invoice_line_ids.filtered(lambda l: not l.display_type and l.move_id.state == 'posted'):
            line_count += 1
            done_moves_related = line.sale_line_ids.mapped('move_ids').filtered(lambda m: m.state == 'done' and m.location_dest_id.usage == 'customer')
            if len(done_moves_related) <= 1:
                if done_moves_related and line_count not in invoice_line_pickings.get(done_moves_related.picking_id, []):
                    invoice_line_pickings.setdefault(done_moves_related.picking_id, []).append(line_count)
            else:
                total_invoices = done_moves_related.mapped('sale_line_id.invoice_lines').filtered(
                    lambda m: m.move_id.state == 'posted' and m.move_id.type == 'out_invoice').sorted(lambda m: m.move_id.invoice_date)
                total_invs = [(i.product_uom_id._compute_quantity(i.quantity, i.product_id.uom_id), i) for i in total_invoices]

                inv = total_invs.pop(0)
                # Match all moves and related invoice lines FIFO looking for when the matched invoice_line matches line
                for move in done_moves_related.sorted(lambda m: m.date):
                    move_qty = move.product_qty
                    while (move_qty > 0):
                        if inv[0] > move_qty:
                            inv = (inv[0] - move_qty, inv[1])
                            invoice_line = inv[1]
                            move_qty = 0
                        if inv[0] <= move_qty:
                            move_qty -= inv[0]
                            invoice_line = inv[1]
                            if total_invs:
                                inv = total_invs.pop(0)
                            else:
                                move_qty = 0 #abort when not enough matched invoices
                        # If in our FIFO iteration we stumble upon the line we were checking
                        if invoice_line == line and line_count not in invoice_line_pickings.get(move.picking_id, []):
                            invoice_line_pickings.setdefault(move.picking_id, []).append(line_count)
        return invoice_line_pickings

    @api.depends('invoice_line_ids', 'invoice_line_ids.sale_line_ids')
    def _compute_ddt_ids(self):
        it_out_invoices = self.filtered(lambda i: i.type == 'out_invoice' and i.company_id.country_id == 'IT')
        for invoice in it_out_invoices:
            invoice_line_pickings = invoice._get_ddt_values()
            pickings = self.env['stock.picking']
            for picking in invoice_line_pickings:
                pickings |= picking
            invoice.picking_ids = pickings
        for invoice in self - it_out_invoices:
            invoice.picking_ids = self.env['stock.picking']

    def _export_as_xml(self, template_values):
        template_values['ddt_dict'] = self._get_ddt_values()
        content = self.env.ref('l10n_it_edi.account_invoice_it_FatturaPA_export').render(template_values)
        return content
