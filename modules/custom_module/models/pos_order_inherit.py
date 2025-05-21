from odoo import models, fields, api, tools
import logging
_logger = logging.getLogger(__name__)


class PosOrder(models.Model):
    _inherit = 'pos.order'

    @api.model
    def sync_from_ui(self, orders):
        print('sync_from_ui', orders)
        odoo_secret_key = tools.config.get("odoo_secret_key")
        print("odoo_secret_key", odoo_secret_key)
        result = super().sync_from_ui(orders)
        for order in orders:
            print("order => ", order)
        print('result of super', result)
        return result
