# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

class SaleOrderCouponPoints(models.Model):
    _name = 'sale.order.coupon.points'
    _description = 'Sale Order Coupon Points - Keeps track of how a sale order impacts a coupon'

    order_id = fields.Many2one('sale.order', required=True, ondelete='cascade')
    coupon_id = fields.Many2one('loyalty.card', required=True, ondelete='cascade')
    points = fields.Float(required=True)

    _sql_constraints = [
        ('order_coupon_unique', 'UNIQUE (order_id, coupon_id)',
        'The coupon points entry already exists.')
    ]
