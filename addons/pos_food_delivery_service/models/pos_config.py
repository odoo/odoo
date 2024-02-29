from odoo import api, fields, models


class PosConfig(models.Model):
    _inherit = "pos.config"

    delivery_provider_ids = fields.Many2many('pos.online.delivery.provider', 'pos_config_delivery_provider_rel', 'config_id', 'delivery_provider_id', string='Delivery Provider')

    def get_delivery_order_count(self):
        # overriden by delivery_provider modules
        # should return a dict with the count of delivery orders for each delivery service
        # like
        # { 
        #   'deliveroo': {
        #       'awaiting': 2,
        #       'preparing': 1
        #   },
        #   'ubereats': {
        #       'awaiting': 1
        #   }
        #}
        return {}
    
    def _send_delivery_order_count(self, order_id):
        order_count = self.get_delivery_order_count()
        if self.current_session_id:
            self._notify('DELIVERY_ORDER_COUNT', order_count, private=False)