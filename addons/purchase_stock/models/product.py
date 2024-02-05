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
            return self.env['stock.route'].search([('id', '=', buy_route.id)]).ids
        return []

    route_ids = fields.Many2many(default=lambda self: self._get_buy_route())


class ProductProduct(models.Model):
    _name = 'product.product'
    _inherit = 'product.product'

    purchase_order_line_ids = fields.One2many('purchase.order.line', 'product_id', string="PO Lines") # used to compute quantities

    def _get_quantity_in_progress(self, location_ids=False, warehouse_ids=False):
        if not location_ids:
            location_ids = []
        if not warehouse_ids:
            warehouse_ids = []

        qty_by_product_location, qty_by_product_wh = super()._get_quantity_in_progress(location_ids, warehouse_ids)
        domain = self._get_lines_domain(location_ids, warehouse_ids)
        groups = self.env['purchase.order.line']._read_group(domain,
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
            qty_by_product_wh[(product.id, location.warehouse_id.id)] += product_qty
        return qty_by_product_location, qty_by_product_wh

    def _get_lines_domain(self, location_ids=False, warehouse_ids=False):
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
        return domain


class SupplierInfo(models.Model):
    _inherit = 'product.supplierinfo'

    last_purchase_date = fields.Date('Last Purchase', compute='_compute_last_purchase_date')
    show_set_supplier_button = fields.Boolean(
        'Show Set Supplier Button', compute='_compute_show_set_supplier_button')

    def _compute_last_purchase_date(self):
        self.last_purchase_date = False
        purchases = self.env['purchase.order'].search([
            ('state', 'in', ('purchase', 'done')),
            ('order_line.product_id', 'in',
             self.product_tmpl_id.product_variant_ids.ids),
            ('partner_id', 'in', self.partner_id.ids),
        ], order='date_order')
        for supplier in self:
            products = supplier.product_tmpl_id.product_variant_ids
            for purchase in purchases:
                if purchase.partner_id != supplier.partner_id:
                    continue
                if not (products & purchase.order_line.product_id):
                    continue
                supplier.last_purchase_date = purchase.date_order
                break

    def _compute_show_set_supplier_button(self):
        self.show_set_supplier_button = True
        orderpoint_id = self.env.context.get('default_orderpoint_id')
        orderpoint = self.env['stock.warehouse.orderpoint'].browse(orderpoint_id)
        if orderpoint_id:
            self.filtered(
                lambda s: s.id == orderpoint.supplier_id.id
            ).show_set_supplier_button = False

    def action_set_supplier(self):
        self.ensure_one()
        orderpoint_id = self.env.context.get('orderpoint_id')
        orderpoint = self.env['stock.warehouse.orderpoint'].browse(orderpoint_id)
        if not orderpoint:
            return
        orderpoint.route_id = self.env['stock.rule'].search([('action', '=', 'buy')], limit=1).route_id.id
        orderpoint.supplier_id = self
        supplier_min_qty = self.product_uom._compute_quantity(self.min_qty, orderpoint.product_id.uom_id)
        if orderpoint.qty_to_order < supplier_min_qty:
            orderpoint.qty_to_order = supplier_min_qty
