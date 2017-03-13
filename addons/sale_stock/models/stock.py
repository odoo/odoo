# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class StockLocationRoute(models.Model):
    _inherit = "stock.location.route"

    sale_selectable = fields.Boolean("Selectable on Sales Order Line")


class StockMove(models.Model):
    _inherit = "stock.move"

    to_refund_so = fields.Boolean(
        "To Refund in SO", default=False,
        help='Trigger a decrease of the delivered quantity in the associated Sales Order')

    @api.multi
    def action_done(self):
        result = super(StockMove, self).action_done()

        # Update delivered quantities on sales order lines
        sale_order_lines = self.filtered(lambda move: move.procurement_id.sale_line_id and move.product_id.expense_policy == 'no').mapped('procurement_id.sale_line_id')
        for line in sale_order_lines:
            line.qty_delivered = line._get_delivered_qty()
        return result

    @api.multi
    def assign_picking(self):
        result = super(StockMove, self).assign_picking()
        for move in self:
            if move.picking_id and move.picking_id.group_id:
                picking = move.picking_id
                order = self.env['sale.order'].search([('procurement_group_id', '=', picking.group_id.id)])
                picking.message_post_with_view(
                    'mail.message_origin_link',
                    values={'self': picking, 'origin': order},
                    subtype_id=self.env.ref('mail.mt_note').id)
        return result


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    sale_id = fields.Many2one('sale.order', "Sales Order", compute='_compute_sale_id', search='_search_sale_id')

    @api.one
    @api.depends('move_lines.procurement_id.sale_line_id.order_id')
    def _compute_sale_id(self):
        for move in self.move_lines:
            if move.procurement_id.sale_line_id:
                self.sale_id = move.procurement_id.sale_line_id.order_id
                return

    def _search_sale_id(self, operator, value):
        moves = self.env['stock.move'].search(
            [('picking_id', '!=', False), ('procurement_id.sale_line_id.order_id', operator, value)]
        )
        return [('id', 'in', moves.mapped('picking_id').ids)]

    @api.multi
    def _create_backorder(self, backorder_moves=[]):
        res = super(StockPicking, self)._create_backorder(backorder_moves)
        for picking in self.filtered(lambda pick: pick.picking_type_id.code == 'outgoing'):
            backorder = picking.search([('backorder_id', '=', picking.id)])
            if backorder.group_id: # origin from a sale
                order = self.env['sale.order'].search([('procurement_group_id', '=', backorder.group_id.id)])
                backorder.message_post_with_view(
                    'mail.message_origin_link',
                    values={'self': backorder, 'origin': order},
                    subtype_id=self.env.ref('mail.mt_note').id)
        return res


class StockReturnPicking(models.TransientModel):
    _inherit = "stock.return.picking"

    @api.multi
    def _create_returns(self):
        new_picking_id, pick_type_id = super(StockReturnPicking, self)._create_returns()
        new_picking = self.env['stock.picking'].browse([new_picking_id])
        for move in new_picking.move_lines:
            return_picking_line = self.product_return_moves.filtered(lambda r: r.move_id == move.origin_returned_move_id)
            if return_picking_line and return_picking_line.to_refund_so:
                move.to_refund_so = True

        return new_picking_id, pick_type_id


class StockReturnPickingLine(models.TransientModel):
    _inherit = "stock.return.picking.line"

    to_refund_so = fields.Boolean(string="To Refund", help='Trigger a decrease of the delivered quantity in the associated Sales Order')
