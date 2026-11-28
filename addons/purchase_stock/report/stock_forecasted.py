# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import defaultdict

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
        groups = self.env['purchase.order.line'].sudo()._read_group(domain,
            ['order_id', 'product_id'],
            ['id:array_agg', 'product_uom_qty:sum'],
        )
        in_qty = defaultdict(float)
        for _order, product, _ids, qty in self.env['purchase.order.line']._get_countable_rfq_groups(groups):
            in_qty[product.id] += qty
        self._add_product_quantities(res, product_template_ids, product_ids, 'draft_purchase_qty', in_qty)
        # All RFQs displayed, even the alternatives that are not counted.
        orders_by_product = defaultdict(self.env['purchase.order'].sudo)
        line_ids_by_product = defaultdict(set)
        for order, product, line_ids, _qty in groups:
            orders_by_product[product.id] |= order
            line_ids_by_product[product.id].update(line_ids)
        for product in self._get_products(product_template_ids, product_ids):
            if product.id in orders_by_product:
                values = res['product'][product.id]
                values['draft_purchase_orders'] = orders_by_product[product.id].sorted('name').read(['id', 'name'])
                values['draft_purchase_orders_matched'] = self.env.context.get('purchase_line_to_match_id') in line_ids_by_product[product.id]
        return res

    def _product_purchase_domain(self, product_template_ids, product_ids):
        if product_ids:
            return [('product_id', 'in', product_ids)]
        elif product_template_ids:
            subquery_products = self.env['product.product']._search(
                [('product_tmpl_id', 'in', product_template_ids)]
            )
            return [('product_id', 'in', subquery_products)]
