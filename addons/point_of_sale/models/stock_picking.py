# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api,fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_is_zero, float_compare

from itertools import groupby

class StockPicking(models.Model):
    _inherit='stock.picking'

    pos_session_id = fields.Many2one('pos.session')
    pos_order_id = fields.Many2one('pos.order')

    def _prepare_picking_vals(self, partner, picking_type, location_id, location_dest_id):
        return {
            'partner_id': partner.id if partner else False,
            'user_id': False,
            'picking_type_id': picking_type.id,
            'move_type': 'direct',
            'location_id': location_id,
            'location_dest_id': location_dest_id,
        }


    @api.model
    def _create_picking_from_pos_order_lines(self, location_dest_id, lines, picking_type, partner=False):
        """We'll create some picking based on order_lines"""

        pickings = self.env['stock.picking']
        stockable_lines = lines.filtered(lambda l: l.product_id.type in ['product', 'consu'] and not float_is_zero(l.qty, precision_rounding=l.product_id.uom_id.rounding))
        if not stockable_lines:
            return pickings
        positive_lines = stockable_lines.filtered(lambda l: l.qty > 0)
        negative_lines = stockable_lines - positive_lines

        if positive_lines:
            location_id = picking_type.default_location_src_id.id
            positive_picking = self.env['stock.picking'].create(
                self._prepare_picking_vals(partner, picking_type, location_id, location_dest_id)
            )

            positive_picking._create_move_from_pos_order_lines(positive_lines)
            try:
                with self.env.cr.savepoint():
                    positive_picking._action_done()
            except (UserError, ValidationError):
                pass

            pickings |= positive_picking
        if negative_lines:
            if picking_type.return_picking_type_id:
                return_picking_type = picking_type.return_picking_type_id
                return_location_id = return_picking_type.default_location_dest_id.id
            else:
                return_picking_type = picking_type
                return_location_id = picking_type.default_location_src_id.id

            negative_picking = self.env['stock.picking'].create(
                self._prepare_picking_vals(partner, return_picking_type, location_dest_id, return_location_id)
            )
            negative_picking._create_move_from_pos_order_lines(negative_lines)
            try:
                with self.env.cr.savepoint():
                    negative_picking._action_done()
            except (UserError, ValidationError):
                pass
            pickings |= negative_picking
        return pickings

    def _prepare_stock_move_vals(self, first_line, order_lines):
        return {
            'name': first_line.name,
            'product_uom': first_line.product_id.uom_id.id,
            'picking_id': self.id,
            'picking_type_id': self.picking_type_id.id,
            'product_id': first_line.product_id.id,
            'product_uom_qty': abs(sum(order_lines.mapped('qty'))),
            'state': 'draft',
            'location_id': self.location_id.id,
            'location_dest_id': self.location_dest_id.id,
            'company_id': self.company_id.id,
        }

    def _create_move_from_pos_order_lines(self, lines):
        self.ensure_one()
        lines_by_product = groupby(sorted(lines, key=lambda l: l.product_id.id), key=lambda l: l.product_id.id)
        for product, lines in lines_by_product:
            order_lines = self.env['pos.order.line'].concat(*lines)
            first_line = order_lines[0]
            current_move = self.env['stock.move'].create(
                self._prepare_stock_move_vals(first_line, order_lines)
            )
            confirmed_moves = current_move._action_confirm()
            for move in confirmed_moves:
                if first_line.product_id == move.product_id and first_line.product_id.tracking != 'none':
                    if self.picking_type_id.use_existing_lots or self.picking_type_id.use_create_lots:
                        for line in order_lines:
                            sum_of_lots = 0
                            for lot in line.pack_lot_ids.filtered(lambda l: l.lot_name):
                                if line.product_id.tracking == 'serial':
                                    qty = 1
                                else:
                                    qty = abs(line.qty)
                                ml_vals = move._prepare_move_line_vals()
                                ml_vals.update({'qty_done':qty})
                                if self.picking_type_id.use_existing_lots:
                                    existing_lot = self.env['stock.production.lot'].search([
                                        ('company_id', '=', self.company_id.id),
                                        ('product_id', '=', line.product_id.id),
                                        ('name', '=', lot.lot_name)
                                    ])
                                    if not existing_lot and self.picking_type_id.use_create_lots:
                                        existing_lot = self.env['stock.production.lot'].create({
                                            'company_id': self.company_id.id,
                                            'product_id': line.product_id.id,
                                            'name': lot.lot_name,
                                        })
                                    ml_vals.update({
                                        'lot_id': existing_lot.id,
                                    })
                                else:
                                    ml_vals.update({
                                        'lot_name': lot.lot_name,
                                    })
                                self.env['stock.move.line'].create(ml_vals)
                                sum_of_lots += qty
                            if abs(line.qty) != sum_of_lots:
                                difference_qty = abs(line.qty) - sum_of_lots
                                ml_vals = current_move._prepare_move_line_vals()
                                if line.product_id.tracking == 'serial':
                                    ml_vals.update({'qty_done': 1})
                                    for i in range(int(difference_qty)):
                                        self.env['stock.move.line'].create(ml_vals)
                                else:
                                    ml_vals.update({'qty_done': difference_qty})
                                    self.env['stock.move.line'].create(ml_vals)
                    else:
                        move._action_assign()
                        for move_line in move.move_line_ids:
                            move_line.qty_done = move_line.product_uom_qty
                        if float_compare(move.product_uom_qty, move.quantity_done, precision_rounding=move.product_uom.rounding) > 0:
                            remaining_qty = move.product_uom_qty - move.quantity_done
                            ml_vals = move._prepare_move_line_vals()
                            ml_vals.update({'qty_done':remaining_qty})
                            self.env['stock.move.line'].create(ml_vals)

                else:
                    move._action_assign()
                    for move_line in move.move_line_ids:
                        move_line.qty_done = move_line.product_uom_qty
                    if float_compare(move.product_uom_qty, move.quantity_done, precision_rounding=move.product_uom.rounding) > 0:
                        remaining_qty = move.product_uom_qty - move.quantity_done
                        ml_vals = move._prepare_move_line_vals()
                        ml_vals.update({'qty_done':remaining_qty})
                        self.env['stock.move.line'].create(ml_vals)
                    move.quantity_done = move.product_uom_qty

    def _send_confirmation_email(self):
        # Avoid sending Mail/SMS for POS deliveries
        pickings = self.filtered(lambda p: p.picking_type_id != p.picking_type_id.warehouse_id.pos_type_id)
        return super(StockPicking, pickings)._send_confirmation_email()
