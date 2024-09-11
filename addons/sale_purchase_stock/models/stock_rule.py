from markupsafe import Markup

from odoo import models, _


class StockRule(models.Model):
    _inherit = 'stock.rule'

    def _notify_responsible(self, procurement):
        super()._notify_responsible(procurement)
        origin_order = procurement.values.get('group_id').sale_id if procurement.values.get('group_id') else False
        if origin_order:
            notified_users = procurement.product_id.responsible_id.partner_id | origin_order.user_id.partner_id
            self._post_vendor_notification(origin_order, notified_users, procurement.product_id)
