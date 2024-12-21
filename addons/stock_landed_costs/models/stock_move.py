# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class StockMove(models.Model):
    _inherit = "stock.move"

    def _additional_invoice_value(self, layers):
        """ If a landed cost have an own invoice line, the additional value will not be added to the
        product invoice line. We need to get the value from the landed cost layer."""
        value = super()._additional_invoice_value(layers)
        for layer in layers:
            if layer.stock_landed_cost_id.vendor_bill_id:
                value += layer.value
        return value
