# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.osv import expression


class ProductCategory(models.Model):
    _inherit = "product.category"

    property_account_creditor_price_difference_categ = fields.Many2one(
        'account.account', string="Price Difference Account",
        company_dependent=True, ondelete='restrict',
        help="This account will be used to value price difference between purchase price and accounting cost.")


class ProductTemplate(models.Model):
    _name = 'product.template'
    _inherit = 'product.template'

    property_account_creditor_price_difference = fields.Many2one(
        'account.account', string="Price Difference Account", company_dependent=True, ondelete='restrict',
        help="This account is used in automated inventory valuation to "\
             "record the price difference between a purchase order and its related vendor bill when validating this vendor bill.")

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
        groups = self.env['purchase.order.line'].sudo()._read_group(domain,
            ['order_id', 'product_id', 'product_uom', 'orderpoint_id', 'location_final_id'],
            ['product_qty:sum'])
        for order, product, uom, orderpoint, location_final, product_qty_sum in groups:
            if orderpoint:
                location = orderpoint.location_id
            elif location_final:
                location = location_final
            else:
                location = order.picking_type_id.default_location_dest_id
            product_qty = uom._compute_quantity(product_qty_sum, product.uom_id, round=False)
            qty_by_product_location[(product.id, location.id)] += product_qty
            qty_by_product_wh[(product.id, location.warehouse_id.id)] += product_qty
        return qty_by_product_location, qty_by_product_wh

    def _get_lines_domain(self, location_ids=False, warehouse_ids=False):
        domains = []
        rfq_domain = [
            ('state', 'in', ('draft', 'sent', 'to approve')),
            ('product_id', 'in', self.ids)
        ]
        if location_ids:
            domains.append(expression.AND([rfq_domain, [
                '|',
                '|',
                    ('order_id.picking_type_id.default_location_dest_id', 'in', location_ids),
                    '&',
                        ('move_ids', '=', False),
                        ('location_final_id', 'child_of', location_ids),
                    '&',
                        ('move_dest_ids', '=', False),
                        ('orderpoint_id.location_id', 'in', location_ids)
            ]]))
        if warehouse_ids:
            domains.append(expression.AND([rfq_domain, [
                '|',
                    ('order_id.picking_type_id.warehouse_id', 'in', warehouse_ids),
                    '&',
                        ('move_dest_ids', '=', False),
                        ('orderpoint_id.warehouse_id', 'in', warehouse_ids)
            ]]))
        return expression.OR(domains) if domains else []


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
        ], order='date_order desc')
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
        if 'buy' not in orderpoint.route_id.rule_ids.mapped('action'):
            orderpoint.route_id = self.env['stock.rule'].search([('action', '=', 'buy')], limit=1).route_id.id
        orderpoint.supplier_id = self
        supplier_min_qty = self.product_uom._compute_quantity(self.min_qty, orderpoint.product_id.uom_id)
        if orderpoint.qty_to_order < supplier_min_qty:
            orderpoint.qty_to_order = supplier_min_qty
        if self._context.get('replenish_id'):
            replenish = self.env['product.replenish'].browse(self._context.get('replenish_id'))
            replenish.supplier_id = self
            return {
                'type': 'ir.actions.act_window',
                'name': 'Replenish',
                'res_model': 'product.replenish',
                'res_id': replenish.id,
                'target': 'new',
                'view_mode': 'form',
            }
