# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ReplenishmentReport(models.AbstractModel):
    _inherit = 'report.stock.report_product_product_replenishment'

    def _compute_draft_quantity_count(self, product_template_ids, product_variant_ids, wh_location_ids):
        res = super()._compute_draft_quantity_count(product_template_ids, product_variant_ids, wh_location_ids)
        domain = self._product_sale_domain(product_template_ids, product_variant_ids)
        so_lines = self.env['sale.order.line'].search(domain)
        out_sum = 0
        if so_lines:
            product_uom = so_lines[0].product_id.uom_id
            quantities = so_lines.mapped(lambda line: line.product_uom._compute_quantity(line.product_uom_qty, product_uom))
            out_sum = sum(quantities)
        res['draft_sale_qty'] = out_sum
        res['draft_sale_orders'] = so_lines.mapped("order_id").sorted(key=lambda so: so.name)
        res['draft_sale_orders_matched'] = self.env.context.get('sale_line_to_match_id') in so_lines.ids
        res['qty']['out'] += out_sum
        return res

    def _product_sale_domain(self, product_template_ids, product_variant_ids):
        domain = [('state', 'in', ['draft', 'sent'])]
        if product_template_ids:
            domain += [('product_template_id', 'in', product_template_ids)]
        elif product_variant_ids:
            domain += [('product_id', 'in', product_variant_ids)]
        warehouse_id = self.env.context.get('warehouse', False)
        if warehouse_id:
            domain += [('warehouse_id', '=', warehouse_id)]
        return domain
