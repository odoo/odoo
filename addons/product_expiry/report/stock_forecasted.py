# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import date

from odoo import models
from odoo.tools import float_is_zero, format_date


class StockForecasted_Product_Product(models.AbstractModel):
    _inherit = 'stock.forecasted_product_product'

    def _get_report_header(self, product_template_ids, product_ids, wh_location_ids):
        res = super()._get_report_header(product_template_ids, product_ids, wh_location_ids)
        res["use_expiration_date"] = any(self.env['product.product'].browse(res["product_variants_ids"]).mapped('use_expiration_date'))
        return res

    def _get_quant_domain(self, location_ids, product_ids):
        res = super()._get_quant_domain(location_ids, product_ids)
        if any(self.env['product.product'].browse(product_ids).mapped('use_expiration_date')):
            res += ['|', ('removal_date', '=', False), ('removal_date', '>=', date.today())]
        return res


    def _prepare_report_line(self, quantity, move_out=None, move_in=None, replenishment_filled=True, product=False, reserved_move=False, in_transit=False, read=True):
        res = super()._prepare_report_line(quantity, move_out, move_in, replenishment_filled, product, reserved_move, in_transit, read)
        removal_date = self.env.context.get('removal_date', False)
        if removal_date:
            res["removal_date"] = format_date(self.env, removal_date)
        return res

    def _get_report_lines(self, product_template_ids, product_ids, wh_location_ids, wh_stock_location, read=True):
        res = super()._get_report_lines(product_template_ids, product_ids, wh_location_ids, wh_stock_location, read)
        out = []
        for line in res:
            out.append(line)
            product = self.env['product.product'].browse(line['product']['id'])
            if product.use_expiration_date and not line['document_in'] and not line['reservation'] and not line['in_transit'] and line['replenishment_filled'] and not line['document_out']:
                # If we find a "free quantity" line for a product with expiration dates, we insert the "To remove on" lines here.
                out += [
                    self.with_context(removal_date=removal_date)._prepare_report_line(free_stock, product=product, read=read)
                    for removal_date, free_stock in self.env['stock.quant']._read_group(
                        self._get_quant_domain(wh_location_ids, product.ids),
                        ['removal_date:day'], ['available_quantity:sum']
                    )
                    if not float_is_zero(free_stock, precision_rounding=product.uom_id.rounding)
                ]
        return out
