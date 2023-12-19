from odoo import models, fields
import pytz

class PosOrder(models.Model):
    _inherit = 'pos.order'

    delivery_display = fields.Char('Delivery Display')
    delivery_prepare_for = fields.Datetime('Delivery Prepare For')

    def _export_for_ui(self, order):
        res = super()._export_for_ui(order)
        timezone = pytz.timezone(self._context.get('tz') or self.env.user.tz or 'UTC')
        res['delivery_display'] = order.delivery_display if order.delivery_display else False
        res['delivery_prepare_for'] = str(order.delivery_prepare_for.astimezone(timezone)) if order.delivery_prepare_for else False
        return res
