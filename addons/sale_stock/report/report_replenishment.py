# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class ReplenishmentReport(models.AbstractModel):
    _inherit = 'report.stock.report_product_product_replenishment'

    @api.model
    def _get_report_data(self, product_template_ids=False, product_variant_ids=False):
        res = super()._get_report_data(product_template_ids, product_variant_ids)
        domain = self._product_sale_domain(product_template_ids, product_variant_ids)
        so_lines = self.env['sale.order.line'].search(domain)
        qty_out = 0
        if so_lines:
            product_uom = so_lines[0].product_id.uom_id
            quantities = so_lines.mapped(lambda line: line.product_uom._compute_quantity(line.product_uom_qty, product_uom))
            qty_out = sum(quantities)
        res['draft_sale_qty'] = qty_out
        res['qty']['out'] += qty_out
        return res

    @api.model
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
