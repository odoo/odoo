# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _is_reorder_allowed(self):
        # Don't allow courses in reorder
        return self.service_tracking != 'course' and super()._is_reorder_allowed()
