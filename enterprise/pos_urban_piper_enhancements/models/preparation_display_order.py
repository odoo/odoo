from odoo import models
from odoo.tools.json import scriptsafe as json


class PosPreparationDisplayOrder(models.Model):
    _inherit = 'pos_preparation_display.order'

    def _export_for_ui(self, preparation_display):
        order = super()._export_for_ui(preparation_display)
        if order and self.pos_order_id.delivery_datetime:
            details = json.loads(self.pos_order_id.delivery_json).get('order', {}).get('details', {})
            delivery_datetime = details.get('delivery_datetime', 0)
            order.update({
                'delivery_datetime': delivery_datetime,
            })
        return order
