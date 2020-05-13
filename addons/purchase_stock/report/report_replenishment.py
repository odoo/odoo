# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class ReplenishmentReport(models.AbstractModel):
    _inherit = 'report.stock.report_product_product_replenishment'

    @api.model
    def _get_report_data(self, product_template_ids=False, product_variant_ids=False):
        res = super()._get_report_data(product_template_ids, product_variant_ids)
        domain = [('state', 'in', ['draft', 'sent'])]
        domain += self._product_purchase_domain(product_template_ids, product_variant_ids)
        warehouse_id = self.env.context.get('warehouse', False)
        if warehouse_id:
            domain += [('order_id.picking_type_id.warehouse_id', '=', warehouse_id)]
        qty_in = 0
        po_lines = self.env['purchase.order.line'].read_group(domain, ['product_uom_qty'], 'product_id')
        if po_lines:
            qty_in = sum(line['product_uom_qty'] for line in po_lines)

        res['draft_purchase_qty'] = qty_in
        res['qty']['in'] += qty_in
        return res

    @api.model
    def _product_purchase_domain(self, product_template_ids, product_variant_ids):
        domain = []
        if product_variant_ids:
            domain += [('product_id', 'in', product_variant_ids)]
        elif product_template_ids:
            products = self.env['product.product'].search_read(
                [('product_tmpl_id', 'in', product_template_ids)], ['id']
            )
            product_ids = [product['id'] for product in products]
            domain += [('product_id', 'in', product_ids)]
        return domain
