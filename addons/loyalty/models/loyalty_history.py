# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class LoyaltyHistory(models.Model):
    _name = 'loyalty.history'
    _description = 'Loyalty History'
    _rec_name = 'description'
    _order = 'required_points asc'

    coupon_id = fields.Many2one(
        comodel_name='loyalty.card',
        required=True,
        ondelete='cascade'
    )
    sale_order_id = fields.Many2one(
        comodel_name='sale.order',
        required=True,
    )
    amount = fields.Integer(
        required=True,
    )
