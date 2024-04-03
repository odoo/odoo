# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ChoosePickupPoint(models.TransientModel):
    _name = 'choose.pickup.point'
    _description = 'Pickup Point Selection Wizard'

    order_id = fields.Many2one('sale.order', ondelete="cascade")
    choose_delivery_carrier_id = fields.Many2one('choose.delivery.carrier', ondelete="cascade")
