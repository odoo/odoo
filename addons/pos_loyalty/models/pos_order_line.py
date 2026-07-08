# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    points_cost = fields.Float(help="How many point this reward cost on the coupon.")
    reward_id = fields.Many2one(
        'loyalty.reward',
        "Reward",
        ondelete='restrict',
        help="The reward associated with this line.",
        index='btree_not_null',
    )
    coupon_id = fields.Many2one(
        'loyalty.card',
        "Coupon",
        ondelete='restrict',
        help="The coupon used to claim that reward.",
    )

    @api.model
    def _load_pos_data_fields(self, config):
        params = super()._load_pos_data_fields(config)
        params += ['reward_id', 'coupon_id']
        return params

    def _has_discount(self):
        return super()._has_discount() or (self.is_reward_line and self.reward_id.reward_type == 'discount')

    def _get_discount_amount_for_report(self):
        if self.is_reward_line:
            return abs(self.price_subtotal_incl)
        return super()._get_discount_amount_for_report()
