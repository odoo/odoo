from odoo import api, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class ProductPricelistItem(models.Model):
    _inherit = "product.pricelist.item"

    @api.model
    def _is_discount_feature_enabled(self):
        return self.env["res.groups"]._is_feature_enabled(
            "sale.group_discount_per_so_line",
        )

    def _is_discount_shown(self):
        if not self:
            _debug.logic("discount_not_shown", reason="no_pricelist_rule")
            return False

        self.check_singleton()
        return (
            self._is_discount_feature_enabled() and self.compute_price == "percentage"
        )
