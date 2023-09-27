# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from odoo.exceptions import UserError


class PosLoyaltyPointsChange(models.Model):
    _name = 'pos.loyalty.points.change'
    _description = 'Defines how a POS order will change the points of a loyalty.card'

    order_id = fields.Many2one('pos.order', required=True, ondelete='cascade')
    coupon_id = fields.Many2one('loyalty.card', required=True, ondelete='restrict')
    points = fields.Float(required=True)
    add_points = fields.Boolean('The points should be added to the loyalty.card points. Otherwise, they should be the new value of the loyalty.card points.', default=True)
    is_coupon_created = fields.Boolean('The coupon is created for the order')
    coupon_new_partner_id = fields.Many2one('res.partner')
    temporary_id = fields.Integer('Temporary id used by the current pos_loyalty system')

    _sql_constraints = [
        ('order_coupon_unique', 'UNIQUE (order_id, coupon_id)',
        'The coupon points entry already exists.')
    ]

    def write(self, vals):
        if set(vals.keys()) & {'order_id', 'coupon_id', 'points', 'add_points', 'is_coupon_created', 'coupon_new_partner_id', 'temporary_id'}:
            raise UserError(_('Cannot modify a loyalty points change essential data.'))

        return super().write(vals)
