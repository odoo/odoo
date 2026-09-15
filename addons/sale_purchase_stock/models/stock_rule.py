from odoo import models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class StockRule(models.Model):
    _inherit = "stock.rule"

    def _notify_responsible(self, procurement):
        super()._notify_responsible(procurement)
        references = procurement.values.get("reference_ids")
        origin_orders = references.sale_ids if references else False
        _debug.logic(
            "vendor_notification_recipients",
            product=procurement.product_id,
            orders=origin_orders or None,
            notify=bool(origin_orders),
        )
        if origin_orders:
            notified_users = (
                procurement.product_id.responsible_id.partner_id
                | origin_orders.user_id.partner_id
            )
            _debug.pipeline(
                "vendor_notification_posted",
                orders=origin_orders,
                partners=notified_users,
                product=procurement.product_id,
            )
            self._post_vendor_notification(
                origin_orders, notified_users, procurement.product_id
            )
