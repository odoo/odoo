# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import date

from odoo import models
from odoo.tools import float_is_zero, format_date


class StockForecasted_Product_Product(models.AbstractModel):
    _inherit = 'stock.forecasted_product_product'

    def _get_report_header(self, product_template_ids, product_ids, wh_location_ids):
        res = super()._get_report_header(product_template_ids, product_ids, wh_location_ids)
        res["use_expiration_date"] = any(self.env['product.product'].browse(res["product_variants_ids"]).mapped('use_expiration_date'))
        if res["use_expiration_date"]:
            products = self._get_products(product_template_ids, product_ids)
            for product in products:
                res["product"][product.id]["to_remove_qty"] = res["product"][product.id]['quantity_on_hand'] + res["product"][product.id]['incoming_qty'] - res["product"][product.id]['outgoing_qty'] - res["product"][product.id]['virtual_available']
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

    def _prepare_report_line(self, quantity, move_out=None, move_in=None, replenishment_filled=True, product=False, reserved_move=False, in_transit=False, read=True):
        res = super()._prepare_report_line(quantity, move_out, move_in, replenishment_filled, product, reserved_move, in_transit, read)
        removal_date = self.env.context.get('removal_date')
        if removal_date:
            res["removal_date"] = removal_date if removal_date == -1 else format_date(self.env, removal_date)
        return res

    def _free_stock_lines(self, product, free_stock, moves_data, wh_location_ids, read):
        res = []
        if product.use_expiration_date:
            reserved_expired, unreserved_expired = self.env['stock.quant']._read_group(self._get_expired_quant_domain(wh_location_ids, product), aggregates=['reserved_quantity:sum', 'available_quantity:sum'])[0]
            # Insert the "To remove now" line here, before the free stock line
            if not product.uom_id.is_zero(unreserved_expired):
                res += [self.with_context(removal_date=-1)._prepare_report_line(unreserved_expired, product=product, read=read)]
            # Insert the "To remove on" lines here, before the free stock line

            to_reduce = sum(d['taken_from_stock'] for d in moves_data.values())

            for removal_date, free_stock_at_date in self.env['stock.quant']._read_group(
                    self._get_quant_domain(wh_location_ids, product),
                ['removal_date:day'], ['available_quantity:sum']
            ):
                to_reduce_here = min(to_reduce, free_stock_at_date)
                to_reduce -= to_reduce_here
                free_stock_at_date -= to_reduce_here
                if not float_is_zero(free_stock_at_date, precision_rounding=product.uom_id.rounding) and removal_date:
                    res.append(self.with_context(removal_date=removal_date)._prepare_report_line(free_stock_at_date, product=product, read=read))

            # Compensate for any reserved products that are no longer fresh
            free_stock += reserved_expired
        return res + super()._free_stock_lines(product, free_stock, moves_data, wh_location_ids, read)
