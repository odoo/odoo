from markupsafe import Markup

from odoo import models, _


class StockRule(models.Model):
    _inherit = 'stock.rule'

    def _notify_responsible(self, procurement):
        super()._notify_responsible(procurement)
        origin_orders = procurement.values.get('reference_ids').sale_ids if procurement.values.get('reference_ids') else False
        if origin_orders:
            notified_users = procurement.product_id.responsible_id.partner_id | origin_orders.user_id.partner_id
            self._post_vendor_notification(origin_orders, notified_users, procurement.product_id)
