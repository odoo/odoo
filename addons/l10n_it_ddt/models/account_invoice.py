# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class AccountInvoice(models.Model):
    _inherit = 'account.move'

    def _get_ddt_values(self):
        res = {}
        for line in self.invoice_line_ids.filtered(lambda l: not l.display_type):
            sale_order = line.sale_line_ids.mapped('order_id')
            invoice = sale_order.invoice_ids.filtered(lambda x: x.invoice_date)
            all_inv_qty = {}
            for invoice_line in invoice.mapped('invoice_line_ids').filtered(lambda x: x.product_id == line.product_id):
                all_inv_qty.setdefault(invoice_line, 0)
                all_inv_qty[invoice_line] += invoice_line.quantity
            picking_moves = sale_order.order_line.mapped('move_ids').filtered(lambda x: x.picking_id.date_done and line.product_id in x.mapped('product_id'))
            invoice_line_related_pickings = {}
            for picking_move in picking_moves.sorted(key=lambda x: x.picking_id.date_done, reverse=True):
                qty = picking_move.quantity_done
                for invoice_line, invoice_qty in all_inv_qty.items():
                    qty -= invoice_qty
                    if qty < 0 and not invoice_line_related_pickings:
                        break
                    else:
                        invoice_line_related_pickings.setdefault(invoice_line, {})
                        invoice_line_related_pickings[invoice_line].update({picking_move.picking_id: []})
                        picking_move.picking_id.invoice_ids += line.move_id
                if qty <= 0:
                    break
            res.update(invoice_line_related_pickings.get(line, {}))
        return res

    def _export_as_xml(self, template_values):
        template_values['ddt_dict'] = self._get_ddt_values()
        content = self.env.ref('l10n_it_edi.account_invoice_it_FatturaPA_export').render(template_values)
        return content
