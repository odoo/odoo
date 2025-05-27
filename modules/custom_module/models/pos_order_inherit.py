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
    ticket_number = fields.Integer(string='Ticket Number', help='Ticket number for the order')


    @api.model
    def sync_from_ui(self, orders):
        print('sync_from_ui', orders)
        result = super().sync_from_ui(orders)
        for order in orders:
            # Generate a ticket_number
            if 'ticket_number' not in order:
                order['ticket_number'] = self.get_today_ticket_number()
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

    def get_today_ticket_number(self):
        """Get the count of orders made today (ignoring time)"""
        today = fields.Date.today()
        # Search for orders where the date part of date_order matches today
        orders_today = self.search_count([
            ('date_order', '>=', fields.Datetime.to_string(datetime.combine(today, datetime.min.time()))),
            ('date_order', '<=', fields.Datetime.to_string(datetime.combine(today, datetime.max.time()))),
        ])
        return orders_today + 1

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['ticket_number'] = self.get_today_ticket_number()
        return super().create(vals_list)

