# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class StockForecasted(models.AbstractModel):
    _inherit = 'stock.forecasted_product_product'

    def _get_report_header(self, product_template_ids, product_ids, wh_location_ids):
        res = super()._get_report_header(product_template_ids, product_ids, wh_location_ids)
        domain = [('state', 'in', ['draft', 'sent', 'to approve'])]
        domain += self._product_purchase_domain(product_template_ids, product_ids)
        warehouse_id = self.env['stock.warehouse']._get_warehouse_id_from_context()
        if warehouse_id:
            domain += [('order_id.picking_type_id.warehouse_id', '=', warehouse_id)]
        po_lines = self.env['purchase.order.line'].search(domain)
        in_sum = sum(po_lines.mapped('product_uom_qty'))
        res['draft_purchase_qty'] = in_sum
        res['draft_purchase_orders'] = po_lines.mapped("order_id").sorted(key=lambda po: po.name).read(fields=['id', 'name'])
        res['draft_purchase_orders_matched'] = self.env.context.get('purchase_line_to_match_id') in po_lines.ids
        res['qty']['in'] += in_sum
        return res

    def _product_purchase_domain(self, product_template_ids, product_ids):
        if product_ids:
            return [('product_id', 'in', product_ids)]
        elif product_template_ids:
            subquery_products = self.env['product.product']._search(
                [('product_tmpl_id', 'in', product_template_ids)]
            )
            return [('product_id', 'in', subquery_products)]

    def _reconcile_with_reserved_stock(self, lines, ins, reserved_move, reserved_out, demand_out, out, read):
        if reserved_out > 0 and reserved_move.purchase_line_id:
            demand_out = max(demand_out - reserved_out, 0)
            in_transit = bool(reserved_move.move_orig_ids)
            # set the move_in to WH IN move for POs and delete the move_in after to prevent duplicate line creation
            for index, in_ in enumerate(ins):
                lines.append(self._prepare_report_line(reserved_out, move_in=in_['move'], move_out=out, reserved_move=in_['move'], in_transit=in_transit, read=read))
                del ins[index]
                return demand_out
        else:
            return super()._reconcile_with_reserved_stock(lines, ins, reserved_move, reserved_out, demand_out, out, read)
