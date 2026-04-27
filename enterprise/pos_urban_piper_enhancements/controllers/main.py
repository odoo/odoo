from datetime import datetime, timezone, timedelta
from odoo.addons.pos_urban_piper.controllers.main import PosUrbanPiperController


class PosUrbanPiperEnhancementController(PosUrbanPiperController):

    def after_delivery_order_create(self, delivery_order, details, pos_config_sudo):
        super().after_delivery_order_create(delivery_order, details, pos_config_sudo)
        delivery_time = (details.get('delivery_datetime') - details.get('created')) / (1000*60)
        if int(delivery_time) > int(delivery_order.prep_time):
            delivery_order.delivery_datetime = datetime.fromtimestamp(
                details.get('delivery_datetime') / 1000.0, timezone.utc
            ).replace(tzinfo=None)
