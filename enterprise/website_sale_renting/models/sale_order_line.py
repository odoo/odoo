# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


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
        return self.order_id.website_id.tz or super()._get_tz()

    def _is_reorder_allowed(self):
        if self.is_rental:
            return False
        return super()._is_reorder_allowed()

    def _get_rental_order_line_description(self):
        """ Add timezone of website to sale order line description

        :return: order line description after adding timezone of website
        :rtype: string
        """
        order_line_description = super()._get_rental_order_line_description()
        website = self.order_id.website_id
        if website and website._is_customer_in_the_same_timezone():
            order_line_description += f' ({self.order_id.website_id.tz})'
        return order_line_description
