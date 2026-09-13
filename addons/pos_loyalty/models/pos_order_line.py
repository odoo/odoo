from odoo import api, fields, models


class PosOrderLine(models.Model):
    _inherit = "pos.order.line"

    is_reward_line = fields.Boolean(
        help="Whether this line is part of a reward or not."
    )
    reward_id = fields.Many2one(
        comodel_name="loyalty.reward",
        help="The reward associated with this line.",
        index="btree_not_null",
        ondelete="restrict",
    )
    coupon_id = fields.Many2one(
        comodel_name="loyalty.card",
        help="The coupon used to claim that reward.",
        ondelete="restrict",
    )
    reward_identifier_code = fields.Char(
        help="""
        Technical field used to link multiple reward lines from the same reward together.
    """
    )
    points_cost = fields.Float(help="How many point this reward cost on the coupon.")

    @api.model
    def _load_pos_data_fields(self, config):
        params = super()._load_pos_data_fields(config)
        params += [
            "is_reward_line",
            "reward_id",
            "reward_identifier_code",
            "points_cost",
            "coupon_id",
        ]
        return params
