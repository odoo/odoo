# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class StockLocationRoute(models.Model):
    _inherit = "stock.location.route"
    sale_selectable = fields.Boolean("Selectable on Sales Order Line")


class StockMove(models.Model):
    _inherit = "stock.move"
    sale_line_id = fields.Many2one('sale.order.line', 'Sale Line')

    @api.model
    def _prepare_merge_moves_distinct_fields(self):
        distinct_fields = super(StockMove, self)._prepare_merge_moves_distinct_fields()
        distinct_fields.append('sale_line_id')
        return distinct_fields

    @api.model
    def _prepare_merge_move_sort_method(self, move):
        move.ensure_one()
        keys_sorted = super(StockMove, self)._prepare_merge_move_sort_method(move)
        keys_sorted.append(move.sale_line_id.id)
        return keys_sorted

    def _action_done(self):
        result = super(StockMove, self)._action_done()
        for line in result.mapped('sale_line_id').sudo():
            line.qty_delivered = line._get_delivered_qty()
        return result

    @api.multi
    def write(self, vals):
        res = super(StockMove, self).write(vals)
        if 'product_uom_qty' in vals:
            for move in self:
                if move.state == 'done':
                    sale_order_lines = self.filtered(lambda move: move.sale_line_id and move.product_id.expense_policy == 'no').mapped('sale_line_id')
                    for line in sale_order_lines.sudo():
                        line.qty_delivered = line._get_delivered_qty()
        return res

    def _assign_picking_post_process(self, new=False):
        super(StockMove, self)._assign_picking_post_process(new=new)
        if new and self.sale_line_id and self.sale_line_id.order_id:
            self.picking_id.message_post_with_view(
                'mail.message_origin_link',
                values={'self': self.picking_id, 'origin': self.sale_line_id.order_id},
                subtype_id=self.env.ref('mail.mt_note').id)


class ProcurementGroup(models.Model):
    _inherit = 'procurement.group'

    sale_id = fields.Many2one('sale.order', 'Sale Order')


class ProcurementRule(models.Model):
    _inherit = 'procurement.rule'

    def _get_stock_move_values(self, product_id, product_qty, product_uom, location_id, name, origin, values, group_id):
        result = super(ProcurementRule, self)._get_stock_move_values(product_id, product_qty, product_uom, location_id, name, origin, values, group_id)
        if values.get('sale_line_id', False):
            result['sale_line_id'] = values['sale_line_id']
        return result


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    sale_id = fields.Many2one(related="group_id.sale_id", string="Sales Order", store=True)
