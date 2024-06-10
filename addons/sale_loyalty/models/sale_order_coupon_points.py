# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.addons import sale, loyalty

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .sale_order import SaleOrder
else:
    SaleOrder = sale.models.SaleOrder


class SaleOrderCouponPoints(models.Model):
    _name = 'sale.order.coupon.points'
    _description = 'Sale Order Coupon Points - Keeps track of how a sale order impacts a coupon'

    order_id = fields.Many2one(comodel_name=SaleOrder, required=True, ondelete='cascade')
    coupon_id = fields.Many2one(comodel_name=loyalty.models.LoyaltyCard, required=True, ondelete='cascade')
    points = fields.Float(required=True)

    _sql_constraints = [
        ('order_coupon_unique', 'UNIQUE (order_id, coupon_id)',
        'The coupon points entry already exists.')
    ]
