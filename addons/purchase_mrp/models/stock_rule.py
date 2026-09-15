from markupsafe import Markup

from odoo import models, _


class StockRule(models.Model):
    _inherit = 'stock.rule'

    def _get_preproduction_rules_cache_key(self, product, warehouse):
        return (
            *super()._get_preproduction_rules_cache_key(product, warehouse),
            # Buy routes are valid only when the product has at least one vendor.
            bool(product.seller_ids),
        )

    def _notify_responsible(self, procurement):
        super()._notify_responsible(procurement)
        origin_orders = procurement.values.get('group_id').mrp_production_ids if procurement.values.get('group_id') else False
        if origin_orders:
            notified_users = procurement.product_id.responsible_id.partner_id | origin_orders.user_id.partner_id
            self._post_vendor_notification(origin_orders, notified_users, procurement.product_id)
