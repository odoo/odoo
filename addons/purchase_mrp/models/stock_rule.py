from markupsafe import Markup

from odoo import models, _


class StockRule(models.Model):
    _inherit = 'stock.rule'

    def _notify_responsible(self, procurement):
        super()._notify_responsible(procurement)
        origin_orders = procurement.values.get('group_id').mrp_production_ids if procurement.values.get('group_id') else False
        if origin_orders:
            notified_users = procurement.product_id.responsible_id.partner_id | origin_orders.user_id.partner_id
            self._post_vendor_notification(origin_orders, notified_users, procurement.product_id)
