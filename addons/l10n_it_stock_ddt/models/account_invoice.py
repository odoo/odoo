# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api, fields, _
from odoo.tools.float_utils import float_compare


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_it_ddt_ids = fields.Many2many('stock.picking', compute="_compute_ddt_ids")
    l10n_it_ddt_count = fields.Integer(compute="_compute_ddt_ids")

    def _get_ddt_values(self):
        """
        We calculate the link between the invoice lines and the deliveries related to the invoice through the
        links with the sale order(s).  We assume that the first picking was invoiced first. (FIFO)
        :return: a dictionary with as key the picking and value the invoice line numbers (by counting)
        """
        self.ensure_one()
        # We don't consider returns/credit notes as we suppose they will lead to more deliveries/invoices as well
        if self.move_type != "out_invoice" or self.state != 'posted':
            return {}
        line_count = 0
        invoice_line_pickings = {}
        for line in self.invoice_line_ids.filtered(lambda l: not l.display_type):
            line_count += 1
            done_moves_related = line.sale_line_ids.mapped('move_ids').filtered(lambda m: m.state == 'done' and m.location_dest_id.usage == 'customer')
            if len(done_moves_related) <= 1:
                if done_moves_related and line_count not in invoice_line_pickings.get(done_moves_related.picking_id, []):
                    invoice_line_pickings.setdefault(done_moves_related.picking_id, []).append(line_count)
            else:
                total_invoices = done_moves_related.mapped('sale_line_id.invoice_lines').filtered(
                    lambda l: l.move_id.state == 'posted' and l.move_id.move_type == 'out_invoice').sorted(lambda l: l.move_id.invoice_date)
                total_invs = [(i.product_uom_id._compute_quantity(i.quantity, i.product_id.uom_id), i) for i in total_invoices]
                inv = total_invs.pop(0)
                # Match all moves and related invoice lines FIFO looking for when the matched invoice_line matches line
                for move in done_moves_related.sorted(lambda m: m.date):
                    rounding = move.product_uom.rounding
                    move_qty = move.product_qty
                    while (float_compare(move_qty, 0, precision_rounding=rounding) > 0):
                        if float_compare(inv[0], move_qty, precision_rounding=rounding) > 0:
                            inv = (inv[0] - move_qty, inv[1])
                            invoice_line = inv[1]
                            move_qty = 0
                        if float_compare(inv[0], move_qty, precision_rounding=rounding) <= 0:
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
        it_out_invoices = self.filtered(lambda i: i.move_type == 'out_invoice' and i.company_id.account_fiscal_country_id.code == 'IT')
        for invoice in it_out_invoices:
            invoice_line_pickings = invoice._get_ddt_values()
            pickings = self.env['stock.picking']
            for picking in invoice_line_pickings:
                pickings |= picking
            invoice.l10n_it_ddt_ids = pickings
            invoice.l10n_it_ddt_count = len(pickings)
        for invoice in self - it_out_invoices:
            invoice.l10n_it_ddt_ids = self.env['stock.picking']
            invoice.l10n_it_ddt_count = 0

    def get_linked_ddts(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'name': _("Linked deliveries"),
            'res_model': 'stock.picking',
            'domain': [('id', 'in', self.l10n_it_ddt_ids.ids)],
        }

    def _prepare_fatturapa_export_values(self):
        template_values = super()._prepare_fatturapa_export_values()
        template_values['ddt_dict'] = self._get_ddt_values()
        return template_values
