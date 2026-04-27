# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.addons.sale_subscription.models.sale_order import SUBSCRIPTION_CLOSED_STATE


class StockForecasted(models.AbstractModel):
    _inherit = 'stock.forecasted_product_product'

    def _get_report_header(self, product_template_ids, product_variant_ids, wh_location_ids):
        res = super()._get_report_header(product_template_ids, product_variant_ids, wh_location_ids)
        domain = self._product_active_subscription_domain(product_template_ids, product_variant_ids)
        so_lines = self.env['sale.order.line'].search(domain)
        out_sum = 0
        if so_lines:
            product_uom = so_lines[0].product_id.uom_id
            quantities = so_lines.mapped(lambda line: line.product_uom._compute_quantity(line.product_uom_qty, product_uom))
            out_sum = sum(quantities)
        res['subscription_qty'] = out_sum
        res['subscription_sale_orders'] = so_lines.mapped("order_id").sorted(key=lambda so: so.name).read(fields=['id', 'name'])
        res['qty']['out'] += out_sum
        return res

    def _product_active_subscription_domain(self, product_template_ids, product_variant_ids):
        domain = [
            ('state', '=', 'sale'),
            ('product_template_id.recurring_invoice', '=', True),
            ('order_id.subscription_state', 'not in', SUBSCRIPTION_CLOSED_STATE)
        ]
        if product_template_ids:
            domain += [('product_template_id', 'in', product_template_ids)]
        elif product_variant_ids:
            domain += [('product_id', 'in', product_variant_ids)]
        warehouse_id = self.env['stock.warehouse']._get_warehouse_id_from_context()
        if warehouse_id:
            domain += [('warehouse_id', '=', warehouse_id)]
        return domain

    def _product_sale_domain(self, product_template_ids, product_ids):
        domain = super(StockForecasted, self)._product_sale_domain(product_template_ids, product_ids)
        return domain + [('product_template_id.recurring_invoice', '=', False)]
