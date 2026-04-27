from odoo import models
from odoo.tools.json import scriptsafe as json


class PosPreparationDisplayOrder(models.Model):
    _inherit = 'pos_preparation_display.order'

    def _export_for_ui(self, preparation_display):
        order = super()._export_for_ui(preparation_display)
        if order:
            platform_data = json.loads(self.pos_order_id.delivery_json).get('order', {}).get(
                'details', {}).get('ext_platforms') if self.pos_order_id.delivery_json else False
            order_otp = ''
            if platform_data:
                order_otp = platform_data[0].get('id', {})
            order.update({
                'delivery_status': self.pos_order_id.delivery_status,
                'delivery_provider_id': self.pos_order_id.delivery_provider_id.id,
                'delivery_identifier': self.pos_order_id.delivery_identifier,
                'prep_time': self.pos_order_id.prep_time,
                'order_otp': order_otp,
                'config_id': self.pos_order_id.session_id.config_id.id,
            })
        return order

    def get_preparation_display_order(self, preparation_display_id):
        preparation_display_orders = super().get_preparation_display_order(preparation_display_id)
        return [
            order for order in preparation_display_orders
            if order.get('delivery_status') in (False, 'acknowledged', 'food_ready', 'cancelled')
        ]
