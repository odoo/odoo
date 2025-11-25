# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command, api, models


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    @api.depends('reference_ids', 'reference_ids.sale_ids')
    def _compute_sale_order_count(self):
        super()._compute_sale_order_count()

    def _get_sale_orders(self):
        return super()._get_sale_orders() | self.reference_ids.sale_ids


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    def _prepare_stock_moves(self, picking):
        res = super()._prepare_stock_moves(picking)
        for re in res:
            if self.sale_line_id and re.get('location_final_id'):
                final_loc = self.env['stock.location'].browse(re.get('location_final_id'))
                if final_loc.usage == 'customer' or final_loc.usage == 'transit':
                    re['sale_line_id'] = self.sale_line_id.id
            if self.sale_line_id.route_ids:
                re['route_ids'] = [Command.link(route_id) for route_id in self.sale_line_id.route_ids.ids]
        return res

    def _get_sale_order_line_product(self):
        return self.sale_line_id.product_id

    def _find_candidate(self, product_id, product_qty, product_uom, location_id, name, origin, company_id, values):
        # if this is defined, this is a dropshipping line, so no
        # this is to correctly map delivered quantities to the so lines
        if not values.get('move_dest_ids') and values.get('sale_line_id'):
            lines = self.filtered(lambda po_line: po_line.sale_line_id.id == values['sale_line_id'])
            return super(PurchaseOrderLine, lines)._find_candidate(product_id, product_qty, product_uom, location_id, name, origin, company_id, values)
        return super()._find_candidate(product_id, product_qty, product_uom, location_id, name, origin, company_id, values)

    @api.model
    def _prepare_purchase_order_line_from_procurement(self, product_id, product_qty, product_uom, location_dest_id, name, origin, company_id, values, po):
        res = super()._prepare_purchase_order_line_from_procurement(product_id, product_qty, product_uom, location_dest_id, name, origin, company_id, values, po)
        # only set the sale line id in case of a dropshipping
        if not values.get('move_dest_ids'):
            res['sale_line_id'] = values.get('sale_line_id', False)
        return res
