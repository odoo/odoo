from odoo import api, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.depends("reference_ids", "reference_ids.purchase_ids")
    def _compute_purchase_order_count(self):
        super()._compute_purchase_order_count()

    def _get_purchase_orders(self):
        _debug.logic(
            "purchase_orders_from_references",
            orders=self,
            references=len(self.reference_ids),
        )
        return super()._get_purchase_orders() | self.reference_ids.purchase_ids
