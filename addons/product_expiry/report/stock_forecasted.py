# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import defaultdict
from datetime import date

from odoo import models
from odoo.tools import format_date


class StockForecasted_Product_Product(models.AbstractModel):
    _inherit = 'stock.forecasted_product_product'

    def _get_report_header(self, product_template_ids, product_ids, wh_location_ids):
        res = super()._get_report_header(product_template_ids, product_ids, wh_location_ids)
        res["use_expiration_date"] = any(self.env['product.product'].browse(res["product_variants_ids"]).mapped('use_expiration_date'))
        if res["use_expiration_date"]:
            for product, qties in res['product'].items():
                res['product'][product]['to_remove_qty'] = qties['qty_available'] + qties['incoming_qty'] - qties['outgoing_qty'] - qties['virtual_available']
        return res

    def _get_quant_domain(self, location_ids, products):
        res = super()._get_quant_domain(location_ids, products)
        if any(products.mapped('use_expiration_date')):
            res += ['|', ('removal_date', '=', False), ('removal_date', '>', date.today())]
        return res

    def _get_expired_quant_domain(self, location_ids, products):
        res = super()._get_quant_domain(location_ids, products)
        res += [('removal_date', '<=', date.today())]
        return res

    def _prepare_report_line(self, quantity, move_out=None, move_in=None, warehouse_id=None, replenishment_filled=True, product=False, reserved_move=False, in_transit=False, read=True):
        res = super()._prepare_report_line(quantity, move_out, move_in, warehouse_id, replenishment_filled, product, reserved_move, in_transit, read)
        removal_date = self.env.context.get('removal_date')
        if removal_date:
            res["removal_date"] = removal_date if removal_date == -1 else format_date(self.env, removal_date)
        return res

    def _free_stock_lines(self, product, free_stock, moves_data, wh_location_ids, wh_with_lines, read):
        res = []
        if product.use_expiration_date:
            for warehouse, reserved_expired, unreserved_expired in self.env['stock.quant']._read_group(
                self._get_expired_quant_domain(wh_location_ids, product),
                ['warehouse_id'], ['reserved_quantity:sum', 'available_quantity:sum']
            ):
                # Insert the "To remove now" line here, before the free stock line
                if not product.uom_id.is_zero(unreserved_expired):
                    res += [self.with_context(removal_date=-1)._prepare_report_line(unreserved_expired, warehouse_id=warehouse.id, product=product, read=read)]
                # Insert the "To remove on" lines here, before the free stock line

                # Compensate for any reserved products that are no longer fresh
                free_stock[warehouse.id] += reserved_expired

            to_reduce = defaultdict(float)
            for move, data in moves_data.items():
                to_reduce[move.location_id.warehouse_id.id] += data['taken_from_stock']

            for removal_date, warehouse, free_stock_at_date in self.env['stock.quant']._read_group(
                    self._get_quant_domain(wh_location_ids, product),
                ['removal_date:day', 'warehouse_id'], ['available_quantity:sum']
            ):
                to_reduce_here = min(to_reduce[warehouse.id], free_stock_at_date)
                to_reduce[warehouse.id] -= to_reduce_here
                free_stock_at_date -= to_reduce_here
                if not product.uom_id.is_zero(free_stock_at_date) and removal_date:
                    res.append(self.with_context(removal_date=removal_date)._prepare_report_line(free_stock_at_date, warehouse_id=warehouse.id, product=product, read=read))

        return res + super()._free_stock_lines(product, free_stock, moves_data, wh_location_ids, wh_with_lines, read)


StockForecasted_Product_Product._get_expired_quant_domain.__override__ = False  # whitelist super()
