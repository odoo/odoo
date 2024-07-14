# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.http import request


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _get_rental_pricing_description(self):
        self.ensure_one()
        order = self.order_id
        pricing = self.product_id._get_best_pricing_rule(
            start_date=order.rental_start_date,
            end_date=order.rental_return_date,
            pricelist=order.pricelist_id,
            company=order.company_id,
            currency=order.currency_id,
        )
        return pricing.description

    def _get_tz(self):
        return request and request.httprequest.cookies.get('tz') or super()._get_tz()

    def _is_reorder_allowed(self):
        if self.is_rental:
            return False
        return super()._is_reorder_allowed()
