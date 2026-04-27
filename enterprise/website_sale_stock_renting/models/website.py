# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class Website(models.Model):
    _inherit = 'website'

    def _get_product_available_qty(self, product, **kwargs):
        stock_quantity = super()._get_product_available_qty(product, **kwargs)
        if product.rent_ok and product.is_storable:
            start_date = kwargs.get('start_date') or product.env.context.get('start_date')
            end_date = kwargs.get('end_date') or product.env.context.get('end_date')
            if end_date and start_date:
                return min(
                    avail['quantity_available']
                    for avail in product.sudo()._get_availabilities(
                        start_date, end_date, self.warehouse_id.id
                    )
                )
        return stock_quantity
