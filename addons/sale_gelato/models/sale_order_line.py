from odoo import api, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    @api.model_create_multi
    def create(self, vals_list):
        order_lines = super().create(vals_list)
        _debug.lifecycle("create", lines=order_lines, rows=len(vals_list))
        order_lines.order_id._prevent_mixing_gelato_and_non_gelato_products()
        return order_lines

    def write(self, vals):
        res = super().write(vals)
        _debug.lifecycle("write", lines=self, fields=list(vals))
        self.order_id._prevent_mixing_gelato_and_non_gelato_products()
        return res
