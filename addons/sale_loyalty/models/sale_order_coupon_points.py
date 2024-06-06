# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class SaleOrderCouponPoints(models.Model):
    _name = 'sale.order.coupon.points'
    _description = 'Sale Order Coupon Points - Keeps track of how a sale order impacts a coupon'

    order_id = fields.Many2one(comodel_name='sale.order', required=True, ondelete='cascade')
    coupon_id = fields.Many2one(comodel_name='loyalty.card', required=True, ondelete='cascade')
    points = fields.Float(required=True)

    program_name = fields.Char(related="coupon_id.program_id.name")
    program_type = fields.Selection(related="coupon_id.program_id.program_type")
    # loyalty_points = fields.Float(default=0)
    # loyalty_new_points = fields.Float(compute='_compute_loyalty_new_points')
    balance = fields.Float(default=0)
    used = fields.Float(default=0)
    issued = fields.Float(default=0)

    # def _compute_loyalty_new_points(self):
    #     for record in self:
    #         record.loyalty_new_points = record.loyalty_points - record.loyalty_used + record.loyalty_issued

    _sql_constraints = [
        ('order_coupon_unique', 'UNIQUE (order_id, coupon_id)',
        'The coupon points entry already exists.')
    ]
