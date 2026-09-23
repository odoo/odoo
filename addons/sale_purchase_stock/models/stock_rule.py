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

    def _update_purchase_order_line(self, product_id, product_qty, product_uom, company_id, values, line):
        res = super()._update_purchase_order_line(product_id, product_qty, product_uom, company_id, values, line)
        if (so_line := values.get('move_dest_ids').sale_line_id) and so_line.state == 'cancel':
            res['product_qty'] = line.product_qty
        return res
