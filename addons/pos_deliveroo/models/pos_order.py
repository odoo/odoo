from odoo import models, fields
import pytz

class PosOrder(models.Model):
    _inherit = 'pos.order'

    delivery_display = fields.Char('Delivery Display')
    delivery_prepare_for = fields.Datetime('Delivery Prepare For')
    delivery_asap = fields.Boolean('Delivery ASAP', default=True)
    delivery_confirm_at = fields.Datetime('Delivery Confirm At')
    delivery_start_preparing_at = fields.Datetime('Delivery Start Preparing At')

    def _export_for_ui(self, order):
        res = super()._export_for_ui(order)
        timezone = pytz.timezone(self._context.get('tz') or self.env.user.tz or 'UTC')
        res['delivery_display'] = order.delivery_display if order.delivery_display else False
        res['delivery_prepare_for'] = str(order.delivery_prepare_for.astimezone(timezone)) if order.delivery_prepare_for else False
        res['delivery_asap'] = order.delivery_asap
        res['delivery_confirm_at'] = str(order.delivery_confirm_at.astimezone(timezone)) if order.delivery_confirm_at else False
        res['delivery_start_preparing_at'] = str(order.delivery_start_preparing_at.astimezone(timezone)) if order.delivery_start_preparing_at else False
        return res

    def change_order_delivery_status(self, new_status, send_order_count = True):
        super().change_order_delivery_status(new_status, send_order_count)
        if self.delivery_provider_id.code == 'deliveroo':
            match new_status:
                case 'preparing':
                    self.delivery_provider_id._send_preparation_status(self.delivery_id, 'in_kitchen', 0)
                case 'ready':
                    self.delivery_provider_id._send_preparation_status(self.delivery_id, 'ready_for_collection_soon')
                case 'delivered':
                    self.delivery_provider_id._send_preparation_status(self.delivery_id, 'collected')
                case _:
                    pass
