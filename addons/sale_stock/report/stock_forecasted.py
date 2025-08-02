# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class StockForecasted_Product_Product(models.AbstractModel):
    _inherit = 'stock.forecasted_product_product'

    def _prepare_report_line(self, quantity, move_out=None, move_in=None, replenishment_filled=True, product=False, reserved_move=False, in_transit=False, read=True):
        line = super()._prepare_report_line(quantity, move_out, move_in, replenishment_filled, product, reserved_move, in_transit, read)

        if not move_out or not move_out.picking_id or not move_out.picking_id.sale_id:
            return line

        picking = move_out.picking_id
        # If read is False, line['move_out'] is a stock.move record and will trigger a record update
        if read:
            line['move_out'].update({
                'picking_id': {
                    'id': picking.id,
                    'priority': picking.priority,
                    'sale_id': {
                        'id': picking.sale_id.id,
                        'amount_untaxed': picking.sale_id.amount_untaxed,
                        'currency_id': picking.sale_id.currency_id.read(fields=['id', 'name'])[0],
                        'partner_id': picking.sale_id.partner_id.read(fields=['id', 'display_name'])[0],
                    }
                }
            })
        return line

    def _get_report_data(self, product_template_ids=False, product_ids=False):
        res = super()._get_report_data(product_template_ids, product_ids)
        sale_warehouse_data = self._get_draft_sale_order_data(product_template_ids, product_ids)
        if res['multiple_warehouses']:
            for warehouse in res['warehouses']:
                warehouse_sale_data = sale_warehouse_data.get(warehouse['id'])
                if warehouse_sale_data:
                    warehouse.update({**warehouse_sale_data})
                    warehouse['qty']['out'] += warehouse_sale_data['draft_sale_qty']
        else:
            warehouse_id = res['warehouses'][0]['id']
            warehouse_sale_data = sale_warehouse_data.get(warehouse_id)
            if warehouse_sale_data:
                res.update({
                    **warehouse_sale_data
                })
                res['qty']['out'] += warehouse_sale_data['draft_sale_qty']
        return res

    def _product_sale_domain(self, product_template_ids, product_ids):
        domain = [('state', 'in', ['draft', 'sent'])]
        if product_template_ids:
            domain += [('product_template_id', 'in', product_template_ids)]
        elif product_ids:
            domain += [('product_id', 'in', product_ids)]
        return domain

    def _get_draft_sale_order_data(self, product_template_ids=False, product_ids=False):
        """
        Draft sale order data grouped by warehouse
        :return: Dictionary mapping warehouse_id to draft sale data
        :rtype: dict[int, dict[float | list | bool]]
        """
        domain = self._product_sale_domain(product_template_ids, product_ids)
        grouped_data = dict(
            self.env['sale.order.line'].sudo()._read_group(domain, ['warehouse_id'], aggregates=['id:recordset'])
        )

        sale_data_by_warehouse = {}
        for warehouse in grouped_data:
            so_lines = grouped_data[warehouse]
            out_sum = 0
            if so_lines:
                product_uom = so_lines[0].product_id.uom_id
                quantities = so_lines.mapped(lambda line: line.product_uom_id._compute_quantity(line.product_uom_qty, product_uom))
                out_sum = sum(quantities)
            sale_data_by_warehouse[warehouse.id] = {
                'draft_sale_qty': out_sum,
                'draft_sale_orders': so_lines.mapped("order_id").sorted(key=lambda so: so.name).read(fields=['id', 'name']),
                'draft_sale_orders_matched': self.env.context.get('sale_line_to_match_id') in so_lines.ids
            }
        return sale_data_by_warehouse
