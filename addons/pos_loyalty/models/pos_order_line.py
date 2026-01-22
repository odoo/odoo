# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    is_reward_line = fields.Boolean(
        help="Whether this line is part of a reward or not.")
    reward_id = fields.Many2one(
        'loyalty.reward', "Reward", ondelete='restrict',
        help="The reward associated with this line.", index='btree_not_null')
    coupon_id = fields.Many2one(
        'loyalty.card', "Coupon", ondelete='restrict',
        help="The coupon used to claim that reward.")
    reward_identifier_code = fields.Char(help="""
        Technical field used to link multiple reward lines from the same reward together.
    """)
    points_cost = fields.Float(help="How many point this reward cost on the coupon.")

    @api.model
    def _load_pos_data_fields(self, config):
        params = super()._load_pos_data_fields(config)
        params += ['is_reward_line', 'reward_id', 'reward_identifier_code', 'points_cost', 'coupon_id']
        return params

    def _points_for_correction(self):
        """
        Calculate point cost adjustments for product rewards based on program rules.
        Returns 0 if order doesn't meet minimum amount/quantity requirements.
        Otherwise calculates points based on reward point mode (money or unit).
        """
        self.ensure_one()
        points = 0
        for rule in self.coupon_id.program_id.rule_ids:
            amount_to_compare = self.order_id.amount_total if rule.minimum_amount_tax_mode == "incl" else (self.order_id.amount_total - self.order_id.amount_tax)
            qty_to_compare = sum(line.qty for line in self.order_id.lines.filtered(lambda l: not l.coupon_id) if rule.any_product or (line.product_id in rule.valid_product_ids))
            if rule.minimum_amount > amount_to_compare or rule.minimum_qty > qty_to_compare:
                return points

        if self.reward_id.reward_type == "product":
            for rule in self.coupon_id.program_id.rule_ids.filtered(lambda r: r.reward_point_mode != "order"):
                if rule.reward_point_mode == 'money':
                    points -= self.price_subtotal_incl * rule.reward_point_amount
                elif rule.reward_point_mode == 'unit':
                    points += self.qty * rule.reward_point_amount
        return points
