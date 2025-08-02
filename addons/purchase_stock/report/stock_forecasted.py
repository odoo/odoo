# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class StockForecasted_Product_Product(models.AbstractModel):
    _inherit = 'stock.forecasted_product_product'

    def _get_report_data(self, product_template_ids=False, product_ids=False):
        res = super()._get_report_data(product_template_ids, product_ids)
        if res['multiple_warehouses']:
            for warehouse in res['warehouses']:
                purchase_data = self.with_context(warehouse_id=warehouse['id'])._get_draft_purchase_order_data(product_template_ids, product_ids)
                warehouse.update({**purchase_data})
                warehouse['qty']['in'] += purchase_data['draft_purchase_qty']
        else:
            purchase_data = self.with_context(warehouse_id=res['warehouses'][0]['id'])._get_draft_purchase_order_data(product_template_ids, product_ids)
            res.update({
                **purchase_data
            })
            res['qty']['in'] += purchase_data['draft_purchase_qty']
        return res

    def _product_purchase_domain(self, product_template_ids, product_ids):
        if product_ids:
            return [('product_id', 'in', product_ids)]
        elif product_template_ids:
            subquery_products = self.env['product.product']._search(
                [('product_tmpl_id', 'in', product_template_ids)]
            )
            return [('product_id', 'in', subquery_products)]

    def _get_draft_purchase_order_data(self, product_template_ids=False, product_ids=False):
        """ Draft purchase order data get by warehouse"""
        domain = [('state', 'in', ['draft', 'sent', 'to approve'])]
        domain += self._product_purchase_domain(product_template_ids, product_ids)
        warehouse_id = self.env.context.get('warehouse_id', False)
        if warehouse_id:
            domain += [('order_id.picking_type_id.warehouse_id', '=', warehouse_id)]
            company = self.env['stock.warehouse'].browse(warehouse_id).company_id
        else:
            company = self.env.company
        domain += [('company_id', '=', company.id)]
        po_lines = self.env['purchase.order.line'].sudo().search(domain)
        in_sum = sum(po_lines.mapped('product_uom_qty'))
        return {
            'draft_purchase_qty': in_sum,
            'draft_purchase_orders': po_lines.mapped("order_id").sorted(key=lambda po: po.name).read(fields=['id', 'name']),
            'draft_purchase_orders_matched': self.env.context.get('purchase_line_to_match_id') in po_lines.ids,
        }
