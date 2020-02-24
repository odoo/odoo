# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, _


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    purchase_order_count = fields.Integer(compute='_compute_purchase_order_count',
                                          groups='purchase.group_purchase_user')

    @api.depends('order_line.purchase_line_ids.order_id')
    def _compute_purchase_order_count(self):
        for sale in self:
            sale.purchase_order_count = len(sale._get_purchase_order())

    def _get_purchase_order(self):
        return self.order_line.purchase_line_ids.order_id

    def action_view_purchases(self):
        self.ensure_one()
        purchases = self._get_purchase_order()
        action = {
            'res_model': 'purchase.order',
            'type': 'ir.actions.act_window',
        }
        if len(purchases) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': purchases.id,
            })
        else:
            action.update({
                'name': _('Sources Purchase Orders %s' % self.name),
                'domain': [('id', 'in', purchases.ids)],
                'view_mode': 'tree,form',
            })
        return action


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _compute_is_mto(self):
        super(SaleOrderLine, self)._compute_is_mto()
        for line in self:
            if not line.display_qty_widget or line.is_mto:
                continue
            product_routes = line.route_id or (line.product_id.route_ids + line.product_id.categ_id.total_route_ids)
            for pull_rule in product_routes.mapped('rule_ids'):
                if pull_rule.picking_type_id.sudo().default_location_src_id.usage == 'supplier' and\
                        pull_rule.picking_type_id.sudo().default_location_dest_id.usage == 'customer':
                    line.is_mto = True
                    break

    def _get_qty_procurement(self, previous_product_uom_qty):
        # People without purchase rights should be able to do this operation
        purchase_lines_sudo = self.sudo().purchase_line_ids
        if purchase_lines_sudo.filtered(lambda r: r.state != 'cancel'):
            qty = 0.0
            for po_line in purchase_lines_sudo.filtered(lambda r: r.state != 'cancel'):
                qty += po_line.product_uom._compute_quantity(po_line.product_qty,
                                                             self.product_uom, rounding_method='HALF-UP')
            return qty
        else:
            return super(SaleOrderLine, self)._get_qty_procurement(previous_product_uom_qty=previous_product_uom_qty)
