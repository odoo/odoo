# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class Website(models.Model):
    _inherit = 'website'

    def _get_product_available_qty(self, product):
        stock_quantity = super()._get_product_available_qty(product)
        if product.rent_ok and not product.allow_out_of_stock_order:
            start_date = product.env.context.get('start_date')
            end_date = product.env.context.get('end_date')
            if end_date and start_date:
                return min(
                    avail['quantity_available']
                    for avail in product.sudo()._get_availabilities(
                        start_date, end_date, self._get_warehouse_available())
                )
        return stock_quantity
