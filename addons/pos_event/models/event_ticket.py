# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, api, fields


class EventTicket(models.Model):
    _name = 'event.event.ticket'
    _inherit = ['event.event.ticket', 'pos.load.mixin']

    @api.model
    def _load_pos_data_domain(self, data):
        return [
            ('event_id.is_finished', '=', False),
            ('event_id.company_id', '=', data['pos.config']['data'][0]['company_id']),
            ('product_id', 'in', [product['id'] for product in data['product.product']['data']]),
            '|', ('end_sale_datetime', '>=', fields.Datetime.now()), ('end_sale_datetime', '=', False),
            '|', ('start_sale_datetime', '<=', fields.Datetime.now()), ('start_sale_datetime', '=', False)
        ]

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['id', 'name', 'event_id', 'seats_used', 'seats_available', 'price', 'product_id', 'seats_max', 'start_sale_datetime', 'end_sale_datetime']
