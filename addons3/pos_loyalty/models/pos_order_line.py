# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    is_reward_line = fields.Boolean(
        help="Whether this line is part of a reward or not.")
    reward_id = fields.Many2one(
        'loyalty.reward', "Reward", ondelete='restrict',
        help="The reward associated with this line.")
    coupon_id = fields.Many2one(
        'loyalty.card', "Coupon", ondelete='restrict',
        help="The coupon used to claim that reward.")
    reward_identifier_code = fields.Char(help="""
        Technical field used to link multiple reward lines from the same reward together.
    """)
    points_cost = fields.Float(help="How many point this reward cost on the coupon.")

    def _order_line_fields(self, line, session_id=None):
        res = super()._order_line_fields(line, session_id)
        # coupon_id may be negative in case of new coupons, they will be added after validating the order.
        if 'coupon_id' in res[2] and res[2]['coupon_id'] < 1:
            res[2].pop('coupon_id')
        return res

    def _is_not_sellable_line(self):
        return super().is_not_sellable_line() or self.reward_id

    def _export_for_ui(self, orderline):
        result = super()._export_for_ui(orderline)
        result['is_reward_line'] = orderline.is_reward_line
        result['reward_id'] = orderline.reward_id.id
        result['coupon_id'] = orderline.coupon_id.id
        result['reward_identifier_code'] = orderline.reward_identifier_code
        result['points_cost'] = orderline.points_cost
        return result
