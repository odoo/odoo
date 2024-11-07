# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class SaleOrderCouponPoints(models.Model):
    _name = 'sale.order.coupon.points'
    _description = "Sale Order Coupon Points - Keeps track of how a sale order impacts a coupon"

    order_id = fields.Many2one(comodel_name='sale.order', required=True, ondelete='cascade')
    coupon_id = fields.Many2one(comodel_name='loyalty.card', required=True, ondelete='cascade')
    points = fields.Float(required=True)

    _order_coupon_unique = models.Constraint(
        'UNIQUE (order_id, coupon_id)',
        "The coupon points entry already exists.",
    )
