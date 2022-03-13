# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields

class DeliverCarrier(models.Model):
    _inherit = 'delivery.carrier'

    delivery_type = fields.Selection(
        selection_add=[
            ('onsite', 'On site')
        ],
        ondelete={'onsite': 'set default'},
        required=True)

    pos_ids = fields.One2many('pos.config', 'delivery_carrier_id', string="Related point of sales")

    def onsite_rate_shipment(self, order):
        return {
            'success': True,
            'price': 0.0,
            'error_message': False,
            'warning_message': False
        }
