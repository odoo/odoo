# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, Command, models
from odoo.tools import float_is_zero


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def button_validate(self):
        res = super().button_validate()
        for picking in self:
            if not picking.sale_id or picking.picking_type_code != 'outgoing':
                continue
            company_rec = self.env['res.company']._find_company_from_partner(picking.partner_id.id)
            if company_rec and company_rec.rule_type in ('sale', 'sale_purchase') and company_rec.copy_lots_delivery:
                # Fetch linked Sale Order
                sale_order = picking.sale_id
                purchase_order = self.env['purchase.order'].sudo().search([('name', '=', sale_order.client_order_ref), ('company_id', '=', company_rec.id)])
                # Find corresponding receipt in other company
                receipts = purchase_order.picking_ids.filtered(lambda p: p.picking_type_code == 'incoming')
                if not receipts:
                    continue
                for move in picking.move_ids:
                    if move.state != 'done' or move.product_id.company_id:
                        continue
                    receipt_move = self._find_corresponding_move(move, receipts)
                    if receipt_move:
                        receipt_move.write({
                            'move_line_ids': [
                                *[Command.delete(ml.id) for ml in receipt_move.move_line_ids],
                                *[Command.create(ml_vals) for ml_vals in self._prepare_move_lines(move, receipt_move)],
                            ]})
                        receipt_move.move_line_ids._apply_putaway_strategy()
        return res

    @api.model
    def _find_corresponding_move(self, move_orig, candidate_pickings):
        for move in candidate_pickings.move_ids:
            if move.product_id == move_orig.product_id and not move.picked:
                return move
        return False

    @api.model
    def _prepare_move_lines(self, delivery_move, receipt_move):
        move_lines_vals = []
        for move_line in delivery_move.move_line_ids:
            ml_vals = receipt_move._prepare_move_line_vals(quantity=0)
            if move_line.lot_id:
                ml_vals['lot_name'] = move_line.lot_id.name
            ml_vals['quantity'] = move_line.quantity
            ml_vals['picked'] = True
            move_lines_vals.append(ml_vals)
        return move_lines_vals
