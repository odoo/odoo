from odoo import models


class ChooseDeliveryCarrier(models.TransientModel):
    _inherit = 'choose.delivery.carrier'

    def _is_in_stock(self, wh_id):
        return self.order_id._is_in_stock(wh_id)
