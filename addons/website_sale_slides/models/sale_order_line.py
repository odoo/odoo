# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _is_custom_cart_line(self):
        # Course registration lines should not be modified during the ecommerce checkout.
        return super()._is_custom_cart_line() or self.service_tracking == 'course'
