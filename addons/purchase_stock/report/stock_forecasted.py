# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class StockForecasted_Product_Product(models.AbstractModel):
    _inherit = 'stock.forecasted_product_product'

    def _get_report_header(self, product_template_ids, product_ids, wh_location_ids):
        res = super()._get_report_header(product_template_ids, product_ids, wh_location_ids)
        domain = [('state', 'in', ['draft', 'sent', 'to approve'])]
        domain += self._product_purchase_domain(product_template_ids, product_ids)
        warehouse_id = self.env.context.get('warehouse_id', False)
        if warehouse_id:
            domain += [('order_id.picking_type_id.warehouse_id', '=', warehouse_id)]
            company = self.env['stock.warehouse'].browse(warehouse_id).company_id
        else:
            company = self.env.company
        domain += [('company_id', '=', company.id)]
        po_lines = self.env['purchase.order.line'].sudo().search(domain).grouped(lambda l: (l.product_id, l.order_id.picking_type_id.warehouse_id))
        in_qty = {(f'{k[0].id}_{k[1].id}'): sum(v.mapped('product_uom_qty')) for k, v in po_lines.items()}
        self._add_product_quantities(res, product_template_ids, product_ids, 'draft_purchase_qty', in_qty)
        for (product, warehouse), lines in po_lines.items():
            product_data = res["product"][f"{product.id}_{warehouse.id}"]
            product_data["draft_purchase_orders"] = (
                lines.mapped("order_id")
                .sorted(key=lambda po: po.name)
                .read(["id", "name"])
            )

            product_data["draft_purchase_orders_matched"] = (
                self.env.context.get("purchase_line_to_match_id") in lines.ids
            )
        return res

    def _product_purchase_domain(self, product_template_ids, product_ids):
        if product_ids:
            return [('product_id', 'in', product_ids)]
        elif product_template_ids:
            subquery_products = self.env['product.product']._search(
                [('product_tmpl_id', 'in', product_template_ids)]
            )
            return [('product_id', 'in', subquery_products)]
