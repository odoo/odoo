from odoo import models, fields, api, tools
import requests
import logging
import json
from datetime import datetime

_logger = logging.getLogger(__name__)


class PosOrder(models.Model):
    _inherit = 'pos.order'

    menupro_id = fields.Char(string='MenuPro ID')
    origine = fields.Char(string='Origine')

    @api.model
    def sync_from_ui(self, orders):
        print('sync_from_ui', orders)
        result = super().sync_from_ui(orders)
        for order in orders:
            print("order => ", order)
        print('result of super', result)
        return result

    @api.model
    def _sync_to_menupro(self, payload):
        restaurant_id = self.env['ir.config_parameter'].sudo().get_param('restaurant_id')
        odoo_secret_key = tools.config.get("odoo_secret_key")
        print("param", odoo_secret_key, restaurant_id)

        # Transform Odoo order to MenuPro format
        #menupro_order = self._transform_order_to_menupro(order)