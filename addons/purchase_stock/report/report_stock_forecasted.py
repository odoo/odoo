# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ReplenishmentReport(models.AbstractModel):
    _inherit = 'report.stock.report_product_product_replenishment'

    def _compute_draft_quantity_count(self, product_template_ids, product_variant_ids, wh_location_ids):
        res = super()._compute_draft_quantity_count(product_template_ids, product_variant_ids, wh_location_ids)
        domain = [('state', 'in', ['draft', 'sent'])]
        domain += self._product_purchase_domain(product_template_ids, product_variant_ids)
        warehouse_id = self.env.context.get('warehouse', False)
        if warehouse_id:
            domain += [('order_id.picking_type_id.warehouse_id', '=', warehouse_id)]
        po_lines = self.env['purchase.order.line'].read_group(domain, ['product_uom_qty'], 'product_id')
        in_sum = sum(line['product_uom_qty'] for line in po_lines)

        res['draft_purchase_qty'] = in_sum
        res['qty']['in'] += in_sum
        return res

    def _product_purchase_domain(self, product_template_ids, product_variant_ids):
        if product_variant_ids:
            return [('product_id', 'in', product_variant_ids)]
        elif product_template_ids:
            products = self.env['product.product'].search_read(
                [('product_tmpl_id', 'in', product_template_ids)], ['id']
            )
            product_ids = [product['id'] for product in products]
            return [('product_id', 'in', product_ids)]
