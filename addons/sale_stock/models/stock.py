# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class StockLocationRoute(models.Model):
    _inherit = "stock.location.route"
    sale_selectable = fields.Boolean("Selectable on Sales Order Line")


class StockMove(models.Model):
    _inherit = "stock.move"
    sale_line_id = fields.Many2one('sale.order.line', 'Sale Line')

    @api.multi
    def action_done(self):
        result = super(StockMove, self).action_done()
        for line in self.mapped('sale_line_id'):
            line.qty_delivered = line._get_delivered_qty()
        return result

class ProcurementGroup(models.Model):
    _inherit = 'procurement.group'

    sale_id = fields.Many2one('sale.order', 'Sale Order')

    def _get_stock_move_values(self, values, rule, group_id):
        result = super(ProcurementGroup, self)._get_stock_move_values(values, rule, group_id)
        if values.get('sale_line_id', False):
            result['sale_line_id'] = values['sale_line_id']
        return result

    @api.multi
    def write(self, vals):
        res = super(StockMove, self).write(vals)
        if 'product_uom_qty' in vals:
            for move in self:
                if move.state == 'done':
                    sale_order_lines = self.filtered(lambda move: move.procurement_id.sale_line_id and move.product_id.expense_policy == 'no').mapped('procurement_id.sale_line_id')
                    for line in sale_order_lines:
                        line.qty_delivered = line._get_delivered_qty()
        return res


class StockPicking(models.Model):
    _inherit = 'stock.picking'


    sale_id = fields.Many2one(related="group_id.sale_id", string="Sales Order", store=True)

    @api.multi
    def _create_backorder(self, backorder_moves=[]):
        res = super(StockPicking, self)._create_backorder(backorder_moves)
        for picking in self.filtered(lambda pick: pick.picking_type_id.code == 'outgoing'):
            backorder = picking.search([('backorder_id', '=', picking.id)])
            if backorder.sale_id:
                backorder.message_post_with_view(
                    'mail.message_origin_link',
                    values={'self': backorder, 'origin': backorder.sale_id},
                    subtype_id=self.env.ref('mail.mt_note').id)
        return res