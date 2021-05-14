# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class PosOrder(models.Model):
    _inherit = 'sale.order'

    pos_order_ids = fields.One2many('pos.order', 'sale_order_origin_id', string="Order Transfered to Point of Sale", readonly=True, groups="point_of_sale.group_pos_user")
    pos_order_line_ids = fields.One2many('pos.order.line', 'sale_order_origin_id', string="Order lines Transfered to Point of Sale", readonly=True, groups="point_of_sale.group_pos_user")
    pos_order_count = fields.Integer(string='Pos Order Count', compute='_count_pos_order', readonly=True, groups="point_of_sale.group_pos_user")

    @api.depends('pos_order_ids')
    def _count_pos_order(self):
        for order in self:
            linked_orders = order.pos_order_ids | order.pos_order_line_ids.mapped('order_id')
            order.pos_order_count = len(linked_orders)

    def action_view_pos_order(self):
        self.ensure_one()
        linked_orders = self.pos_order_ids | self.pos_order_line_ids.mapped('order_id')
        return {
            'type': 'ir.actions.act_window',
            'name': _('Linked POS Orders'),
            'res_model': 'pos.order',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', linked_orders.ids)],
        }

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    pos_order_line_ids = fields.One2many('pos.order.line', 'sale_order_line_id', string="Order lines Transfered to Point of Sale", readonly=True, groups="point_of_sale.group_pos_user")

    @api.depends('pos_order_line_ids.qty')
    def _compute_qty_delivered(self):
        super()._compute_qty_delivered()
        for sale_line in self:
            sale_line.qty_delivered += sum([pos_line.qty for pos_line in sale_line.pos_order_line_ids if sale_line.product_id.type != 'service'], 0)

    @api.depends('pos_order_line_ids.qty')
    def _get_invoice_qty(self):
        super()._get_invoice_qty()
        for sale_line in self:
            sale_line.qty_invoiced += sum([pos_line.qty for pos_line in sale_line.pos_order_line_ids], 0)
