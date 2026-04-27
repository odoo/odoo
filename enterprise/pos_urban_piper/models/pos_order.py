# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo import fields, models


class PosOrder(models.Model):
    _inherit = 'pos.order'

    delivery_status = fields.Selection([
        ('placed', 'Placed'),
        ('acknowledged', 'Acknowledged'),
        ('food_ready', 'Food Ready'),
        ('dispatched', 'Dispatched'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')], string='Delivery Status', help='Status of the order as provided by UrbanPiper.')
    delivery_provider_id = fields.Many2one(
        'pos.delivery.provider',
        string='Delivery Provider',
        help='Responsible delivery provider for online order, e.g., UberEats, Zomato.'
    )
    delivery_identifier = fields.Char(string='Delivery ID', help='Unique delivery ID provided by UrbanPiper.')
    delivery_json = fields.Json(string='Delivery JSON', help='JSON data of the order.', store=True)
    delivery_rider_json = fields.Json(string='Delivery Rider JSON', help='JSON data of the delivery rider.', store=True)
    prep_time = fields.Integer(
        string='Food Preparation Time',
        help='Preparation time for the food as provided by UrbanPiper.'
    )

    def _generate_unique_reference(self, pos_session_id, config_id, sequence_number, delivery_provider):
        """
        Generate unique id for the urban piper order.
        """
        return f'{delivery_provider} {pos_session_id:05}-{config_id:03}-{sequence_number:04}'

    def mark_urbanpiper_prep_order_as_printed(self):
        self.ensure_one()
        # Lock the line
        self.env.cr.execute(
            'SELECT id FROM pos_order WHERE id = %s FOR UPDATE NOWAIT',
            (self.id,)
        )

        lopc = json.loads(self.last_order_preparation_change) if self.last_order_preparation_change else {
            'lines': {},
            'metadata': {},
        }
        if lopc.get('urbanpiper_printed', False):
            raise ValueError("This delivery order has already been printed automatically.")

        lopc['urbanpiper_printed'] = True
        self.last_order_preparation_change = json.dumps(lopc)
