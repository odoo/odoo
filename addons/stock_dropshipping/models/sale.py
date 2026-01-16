# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    dropship_picking_count = fields.Integer("Dropship Count", compute='_compute_picking_ids')

    @api.depends('picking_ids.is_dropship')
    def _compute_picking_ids(self):
        super()._compute_picking_ids()
        for order in self:
            dropship_count = len(order.picking_ids.filtered(lambda p: p.is_dropship))
            order.delivery_count -= dropship_count
            order.dropship_picking_count = dropship_count

    def action_view_delivery(self):
        return self._get_action_view_picking(self.picking_ids.filtered(lambda p: not p.is_dropship))

    def action_view_dropship(self):
        return self._get_action_view_picking(self.picking_ids.filtered(lambda p: p.is_dropship))


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _compute_is_mto(self):
        super(SaleOrderLine, self)._compute_is_mto()
        for line in self:
            if not line.display_qty_widget or line.is_mto:
                continue
            product_routes = line.route_ids or (line.product_id.route_ids + line.product_id.categ_id.total_route_ids)
            for pull_rule in product_routes.mapped('rule_ids'):
                if pull_rule.picking_type_id.sudo().default_location_src_id.usage == 'supplier' and\
                        pull_rule.picking_type_id.sudo().default_location_dest_id.usage == 'customer':
                    line.is_mto = True
                    break

    def _get_qty_procurement(self, previous_product_uom_qty=False):
        # People without purchase rights should be able to do this operation
        purchase_lines_sudo = self.sudo().purchase_line_ids
        # We make sure that it's not a kit with dropshipped components
        if any(pol._is_dropshipped() and pol.state != 'cancel' for pol in purchase_lines_sudo) and\
            self.product_id == purchase_lines_sudo.product_id:
            qty = 0.0
            for po_line in purchase_lines_sudo.filtered(lambda r: r.state != 'cancel'):
                qty += po_line.product_uom_id._compute_quantity(po_line.product_qty, self.product_uom_id, rounding_method='HALF-UP')
            return qty
        else:
            return super(SaleOrderLine, self)._get_qty_procurement(previous_product_uom_qty=previous_product_uom_qty)

    @api.depends('purchase_line_count')
    def _compute_product_updatable(self):
        super()._compute_product_updatable()
        if self.env.user.has_group('purchase.group_purchase_user'):
            for line in self:
                if line.purchase_line_count > 0:
                    line.product_updatable = False

    def _purchase_service_prepare_order_values(self, supplierinfo):
        res = super()._purchase_service_prepare_order_values(supplierinfo)
        dropship_operation = self.env['stock.picking.type'].search([
            ('company_id', '=', res['company_id']),
            ('default_location_src_id.usage', '=', 'supplier'),
            ('default_location_dest_id.usage', '=', 'customer'),
        ], limit=1, order='sequence')
        if dropship_operation:
            res['dest_address_id'] = self.order_id.partner_shipping_id.id
            res['picking_type_id'] = dropship_operation.id
        return res
