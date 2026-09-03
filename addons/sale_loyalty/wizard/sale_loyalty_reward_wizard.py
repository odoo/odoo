# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class SaleLoyaltyRewardWizard(models.TransientModel):
    _name = "sale.loyalty.reward.wizard"
    _description = "Sale Loyalty - Reward Selection Wizard"

    order_id = fields.Many2one(
        "sale.order", default=lambda self: self.env.context.get("active_id"), required=True
    )

    coupon_code = fields.Char(required=False)
    coupon_successfully_applied = fields.Boolean(default=False)
    applied_reward_id = fields.Many2one("loyalty.reward")
    applied_reward_description = fields.Char(compute="_compute_applied_reward_description")
    coupon_reward_label = fields.Char(compute="_compute_coupon_reward_label")
    reward_ids = fields.Many2many("loyalty.reward", compute="_compute_claimable_reward_ids")
    selected_reward_id = fields.Many2one(
        "loyalty.reward",
        domain="[('id', 'in', reward_ids)]",
        compute="_compute_selected_reward_id",
        readonly=False,
        store=True,
    )
    # In case of multi_product reward
    multi_product_reward = fields.Boolean(related="selected_reward_id.multi_product")
    reward_product_ids = fields.Many2many(related="selected_reward_id.reward_product_ids")
    selected_product_id = fields.Many2one(
        "product.product",
        domain="[('id', 'in', reward_product_ids)]",
        compute="_compute_selected_product_id",
        readonly=False,
        store=True,
    )

    @api.depends("order_id", "applied_reward_id")
    def _compute_applied_reward_description(self):
        for wizard in self:
            if wizard.applied_reward_id:
                wizard.applied_reward_description = self.env._(
                    "%s applied!", wizard.applied_reward_id.description
                )
            elif wizard.coupon_successfully_applied:
                wizard.applied_reward_description = self.env._(
                    "Coupon code '%s' applied!", wizard.coupon_code
                )
            else:
                wizard.applied_reward_description = False

    @api.depends("order_id")
    def _compute_coupon_reward_label(self):
        for wizard in self:
            loyalty_points = ", ".join([
                "%s %s" % (wizard.order_id._get_real_points_for_coupon(coupon), coupon.point_name)
                for coupon, rewards in wizard.order_id._get_claimable_and_showable_rewards().items()
                if coupon and rewards and rewards[0].program_id.program_type == "loyalty"
            ])
            wizard.coupon_reward_label = (
                self.env._("Loyalty program (%s)", loyalty_points)
                if loyalty_points
                else self.env._("Loyalty program")
            )

    @api.depends("order_id")
    def _compute_claimable_reward_ids(self):
        for wizard in self:
            if not wizard.order_id:
                wizard.reward_ids = False
            else:
                claimable_reward = wizard.order_id._get_claimable_rewards()
                reward_ids = self.env["loyalty.reward"]
                for rewards in claimable_reward.values():
                    reward_ids |= rewards
                wizard.reward_ids = reward_ids

    @api.depends("reward_ids")
    def _compute_selected_reward_id(self):
        for wizard in self:
            if not wizard.selected_reward_id and wizard.reward_ids:
                wizard.selected_reward_id = wizard.reward_ids[:1]

    @api.depends("reward_product_ids")
    def _compute_selected_product_id(self):
        for wizard in self:
            if wizard.selected_reward_id.reward_type != "product":
                wizard.selected_product_id = False
            else:
                wizard.selected_product_id = wizard.reward_product_ids[:1]

    def action_apply(self):
        self.ensure_one()
        if not self.selected_reward_id:
            raise ValidationError(self.env._("No reward selected."))
        claimable_rewards = self.order_id._get_claimable_rewards()
        selected_coupon = False
        for coupon, rewards in claimable_rewards.items():
            if self.selected_reward_id in rewards:
                selected_coupon = coupon
                break
        if not selected_coupon:
            raise ValidationError(
                self.env._(
                    "Coupon not found while trying to add the following reward: %s",
                    self.selected_reward_id.description,
                )
            )
        self.order_id._apply_program_reward(
            self.selected_reward_id, selected_coupon, product=self.selected_product_id
        )
        self.order_id._update_programs_and_rewards()
        self._unlink_unused_coupon_ids()
        return True

    def action_cancel(self):
        self.ensure_one()
        self._unlink_unused_coupon_ids()

    def action_apply_coupon(self):
        self.ensure_one()
        if not self.order_id:
            raise ValidationError(self.env._("Invalid sales order."))
        status = self.order_id._try_apply_code(self.coupon_code)
        if "error" in status:
            self.coupon_successfully_applied = False
            raise ValidationError(status["error"])
        self.coupon_successfully_applied = True
        if len(status) == 1:
            coupon, rewards = next(iter(status.items()))
            if len(rewards) == 1:
                self.applied_reward_id = rewards
                self.order_id._apply_program_reward(rewards, coupon)
                self.order_id._update_programs_and_rewards()
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "views": [(False, "form")],
            "target": "new",
        }

    def _unlink_unused_coupon_ids(self):
        reward_coupons = self.order_id.order_line.coupon_id
        self.order_id.coupon_point_ids.filtered(
            lambda points: (
                points.coupon_id.program_id.applies_on == "current"
                and points.coupon_id not in reward_coupons
            )
        ).coupon_id.sudo().unlink()
