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
        po_lines = self.env['purchase.order.line'].sudo().search(domain).grouped('product_id')
        in_qty = {k.id: sum(v.mapped('product_uom_qty')) for k, v in po_lines.items()}
        self._add_product_quantities(res, product_template_ids, product_ids, 'draft_purchase_qty', in_qty)
        for product in self._get_products(product_template_ids, product_ids):
            if product not in po_lines:
                continue
            res['product'][product.id]['draft_purchase_orders'] = po_lines[product].mapped("order_id").sorted(key=lambda po: po.name).read(fields=['id', 'name'])
            res['product'][product.id]['draft_purchase_orders_matched'] = self.env.context.get('purchase_line_to_match_id') in po_lines[product].ids
        return res

    def _product_purchase_domain(self, product_template_ids, product_ids):
        if product_ids:
            return [('product_id', 'in', product_ids)]
        elif product_template_ids:
            subquery_products = self.env['product.product']._search(
                [('product_tmpl_id', 'in', product_template_ids)]
            )
            return [('product_id', 'in', subquery_products)]
