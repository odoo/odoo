from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class SaleLoyaltyRewardWizard(models.TransientModel):
    _name = "sale.loyalty.reward.wizard"
    _description = "Sale Loyalty - Reward Selection Wizard"

    order_id = fields.Many2one(
        comodel_name="sale.order",
        default=lambda self: self.env.context.get("active_id"),
        required=True,
    )

    reward_ids = fields.Many2many(
        comodel_name="loyalty.reward",
        compute="_compute_reward_ids",
    )
    selected_reward_id = fields.Many2one(
        comodel_name="loyalty.reward",
        domain="[('id', 'in', reward_ids)]",
    )
    multi_product_reward = fields.Boolean(related="selected_reward_id.multi_product")
    reward_product_ids = fields.Many2many(
        related="selected_reward_id.reward_product_ids"
    )
    selected_product_id = fields.Many2one(
        comodel_name="product.product",
        compute="_compute_selected_product_id",
        store=True,
        readonly=False,
        domain="[('id', 'in', reward_product_ids)]",
    )

    @api.depends("order_id")
    def _compute_reward_ids(self):
        for wizard in self:
            if not wizard.order_id:
                wizard.reward_ids = False
            else:
                claimable_reward = wizard.order_id._get_claimable_rewards()
                reward_ids = self.env["loyalty.reward"]
                for rewards in claimable_reward.values():
                    reward_ids |= rewards
                wizard.reward_ids = reward_ids

    @api.depends("reward_product_ids")
    def _compute_selected_product_id(self):
        for wizard in self:
            if wizard.selected_reward_id.reward_type != "product":
                wizard.selected_product_id = False
            else:
                wizard.selected_product_id = wizard.reward_product_ids[:1]

    def action_apply(self):
        self.check_singleton()
        if not self.selected_reward_id:
            _debug.logic("reward_apply_refused", wizard=self, reason="none_selected")
            raise ValidationError(_("No reward selected."))
        claimable_rewards = self.order_id._get_claimable_rewards()
        selected_coupon = False
        for coupon, rewards in claimable_rewards.items():
            if self.selected_reward_id in rewards:
                selected_coupon = coupon
                break
        if not selected_coupon:
            _debug.logic(
                "reward_apply_refused",
                wizard=self,
                reason="no_coupon_for_reward",
                reward=self.selected_reward_id,
            )
            raise ValidationError(
                _(
                    "Coupon not found while trying to add the following reward: %s",
                    self.selected_reward_id.description,
                )
            )
        _debug.lifecycle(
            "reward_applied",
            order=self.order_id,
            reward=self.selected_reward_id,
            product=self.selected_product_id,
        )
        self.order_id._apply_program_reward(
            self.selected_reward_id, coupon, product=self.selected_product_id
        )
        self.order_id._update_programs_and_rewards()
        self._unlink_unused_coupon_ids()
        return True

    def action_cancel(self):
        self.check_singleton()
        self._unlink_unused_coupon_ids()

    def _unlink_unused_coupon_ids(self):
        reward_coupons = self.order_id.line_ids.coupon_id
        self.order_id.coupon_point_ids.filtered(
            lambda points: (
                points.coupon_id.program_id.applies_on == "current"
                and points.coupon_id not in reward_coupons
            )
        ).coupon_id.sudo().unlink()
