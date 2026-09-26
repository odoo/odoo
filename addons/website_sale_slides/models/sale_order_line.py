# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _is_reorder_allowed(self):
        # Don't allow courses in reorder
        return self.service_tracking != 'course' and super()._is_reorder_allowed()

    def _is_sellable(self):
        """Override of `website_sale` to flag course lines as not sellable, as a course is bought
        once and its cart line isn't meant to be edited.
        """
        return super()._is_sellable() and self.service_tracking != 'course'
