from odoo import models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _action_launch_stock_rule(self, **kwargs):
        gelato_lines = self.filtered(lambda l: l.product_id.gelato_product_uid)
        _debug.logic("stock_rules_skipped", lines=gelato_lines, reason="gelato_product")
        super(SaleOrderLine, self - gelato_lines)._action_launch_stock_rule(**kwargs)
