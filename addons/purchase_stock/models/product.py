# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.osv import expression


class ProductTemplate(models.Model):
    _name = 'product.template'
    _inherit = 'product.template'

    @api.model
    def _get_buy_route(self):
        buy_route = self.env.ref('purchase_stock.route_warehouse0_buy', raise_if_not_found=False)
        if buy_route:
            return buy_route.ids
        return []

    route_ids = fields.Many2many(default=lambda self: self._get_buy_route())


class ProductProduct(models.Model):
    _name = 'product.product'
    _inherit = 'product.product'

    purchase_order_line_ids = fields.One2many('purchase.order.line', 'product_id', help='Technical: used to compute quantities.')

    def _get_quantity_in_progress(self, location_ids=False, warehouse_ids=False):
        if not location_ids:
            location_ids = []
        if not warehouse_ids:
            warehouse_ids = []

        qty_by_product_location, qty_by_product_wh = super()._get_quantity_in_progress(location_ids, warehouse_ids)
        domain = []
        rfq_domain = [
            ('state', 'in', ('draft', 'sent', 'to approve')),
            ('product_id', 'in', self.ids)
        ]
        if location_ids:
            domain = expression.AND([rfq_domain, [
                '|',
                    ('order_id.picking_type_id.default_location_dest_id', 'in', location_ids),
                    '&',
                        ('move_dest_ids', '=', False),
                        ('orderpoint_id.location_id', 'in', location_ids)
            ]])
        if warehouse_ids:
            wh_domain = expression.AND([rfq_domain, [
                '|',
                    ('order_id.picking_type_id.warehouse_id', 'in', warehouse_ids),
                    '&',
                        ('move_dest_ids', '=', False),
                        ('orderpoint_id.warehouse_id', 'in', warehouse_ids)
            ]])
            domain = expression.OR([domain, wh_domain])
        groups = self.env['purchase.order.line'].read_group(domain,
            ['product_id', 'product_qty', 'order_id', 'product_uom', 'orderpoint_id'],
            ['order_id', 'product_id', 'product_uom', 'orderpoint_id'], lazy=False)
        for group in groups:
            if group.get('orderpoint_id'):
                location = self.env['stock.warehouse.orderpoint'].browse(group['orderpoint_id'][:1]).location_id
            else:
                order = self.env['purchase.order'].browse(group['order_id'][0])
                location = order.picking_type_id.default_location_dest_id
            product = self.env['product.product'].browse(group['product_id'][0])
            uom = self.env['uom.uom'].browse(group['product_uom'][0])
            product_qty = uom._compute_quantity(group['product_qty'], product.uom_id, round=False)
            qty_by_product_location[(product.id, location.id)] += product_qty
            qty_by_product_wh[(product.id, location.get_warehouse().id)] += product_qty
        return qty_by_product_location, qty_by_product_wh
