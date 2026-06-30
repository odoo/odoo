# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class StockForecasted_Product_Product(models.AbstractModel):
    _inherit = 'stock.forecasted_product_product'

    def _prepare_report_line(self, quantity, move_out=None, move_in=None, replenishment_filled=True, product=False, reserved_move=False, in_transit=False, read=True):
        line = super()._prepare_report_line(quantity, move_out, move_in, replenishment_filled, product, reserved_move, in_transit, read)

        if not move_out or not move_out.picking_id or not move_out.picking_id.sale_id:
            return line

        picking = move_out.picking_id
        # If read is False, line['move_out'] is a stock.move record and will trigger a record update
        if read:
            line['move_out'].update({
                'picking_id': {
                    'id': picking.id,
                    'priority': picking.priority,
                    'sale_id': {
                        'id': picking.sale_id.id,
                        'amount_untaxed': picking.sale_id.amount_untaxed,
                        'currency_id': picking.sale_id.currency_id.read(fields=['id', 'name'])[0],
                        'partner_id': picking.sale_id.partner_id.read(fields=['id', 'display_name'])[0],
                    }
                }
            })
        return line

    def _get_report_header(self, product_template_ids, product_ids, wh_location_ids):
        res = super()._get_report_header(product_template_ids, product_ids, wh_location_ids)
        domain = self._product_sale_domain(product_template_ids, product_ids)
        so_lines = self.env['sale.order.line'].sudo().search(domain).grouped('product_id')
        out_qty = {k.id: sum(v.mapped(lambda line: line.product_uom_id._compute_quantity(line.product_uom_qty, line.product_id.uom_id))) for k, v in so_lines.items()}
        self._add_product_quantities(res, product_template_ids, product_ids, 'draft_sale_qty', qty_out=out_qty)
        for product in self._get_products(product_template_ids, product_ids):
            if product not in so_lines:
                continue
            res['product'][product.id]['draft_sale_orders'] = so_lines[product].mapped("order_id").sorted(key=lambda so: so.name).read(fields=['id', 'name'])
            res['product'][product.id]['draft_sale_orders_matched'] = self.env.context.get('sale_line_to_match_id') in so_lines[product].ids
        return res

    def _product_sale_domain(self, product_template_ids, product_ids):
        domain = [('state', 'in', ['draft', 'sent'])]
        if product_template_ids:
            domain += [('product_template_id', 'in', product_template_ids)]
        elif product_ids:
            domain += [('product_id', 'in', product_ids)]
        warehouse_id = self.env.context.get('warehouse_id', False)
        if warehouse_id:
            domain += [('warehouse_id', '=', warehouse_id)]
        return domain
