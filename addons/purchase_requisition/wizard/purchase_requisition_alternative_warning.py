# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.tools import OrderedSet


class PurchaseRequisitionAlternativeWarning(models.TransientModel):
    _name = 'purchase.requisition.alternative.warning'
    _description = 'Wizard in case PO still has open alternative requests for quotation'

    po_ids = fields.Many2many('purchase.order', 'warning_purchase_order_rel', string="POs to Confirm")
    alternative_po_ids = fields.Many2many('purchase.order', 'warning_purchase_order_alternative_rel', string="Alternative POs")

    def action_keep_alternatives(self):
        self._set_dest_moves()
        return self._action_done()

    def action_cancel_alternatives(self):
        self._set_dest_moves()
        # in theory alternative_po_ids shouldn't have any po_ids in it, but it's possible by accident/forcing it, so avoid cancelling them to be safe
        self.alternative_po_ids.filtered(lambda po: po.state in ['draft', 'sent', 'to approve'] and po.id not in self.po_ids.ids).button_cancel()
        return self._action_done()

    def _action_done(self):
        return self.po_ids.with_context({'skip_alternative_check': True}).button_confirm()

    def _set_dest_moves(self):
        original_po = self.alternative_po_ids.filtered(lambda po: not po.partner_id)
        if original_po:
            mts_move_ids = OrderedSet()
            for line in original_po.order_line:
                corresponding_lines = self.po_ids.order_line.filtered(lambda l: l.product_id == line.product_id)
                if corresponding_lines:
                    corresponding_lines.move_dest_ids = line.move_dest_ids
                else:
                    mts_move_ids.add(line.move_dest_ids.ids)
            mts_moves = self.env['stock.move'].browse(mts_move_ids)
            mts_moves.write({'procure_method': 'make_to_stock'})
            mts_moves._recompute_state()
            original_po.order_line.move_dest_ids = False
