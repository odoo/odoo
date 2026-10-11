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
    applied_reward_description = fields.Char(compute="_compute_applied_reward_description")
    reward_ids = fields.Many2many("loyalty.reward", compute="_compute_claimable_reward_ids")
    # Claimable rewards grouped by program, to display them under a title with the points
    reward_groups = fields.Json(compute="_compute_claimable_reward_ids")
    selected_reward_ids = fields.Many2many(
        "loyalty.reward",
        relation="sale_loyalty_reward_wizard_selected_reward_rel",
        domain="[('id', 'in', reward_ids)]",
    )
    # Products chosen for the selected rewards letting choose among several products
    selected_product_ids = fields.Many2many("product.product")
    # Coupons entered with a code and offering a single reward, which is selected without showing it
    applied_coupon_ids = fields.Many2many("loyalty.card")

    @api.depends("order_id", "applied_coupon_ids")
    def _compute_claimable_reward_ids(self):
        for wizard in self:
            if not wizard.order_id:
                wizard.reward_ids = False
                wizard.reward_groups = []
                continue
            claimable_rewards = wizard.order_id._get_claimable_rewards()
            reward_ids = self.env["loyalty.reward"].union(claimable_rewards.values())
            wizard.reward_ids = reward_ids.sorted("id")
            wizard.reward_groups = [
                {
                    "coupon_id": coupon.id,
                    "program_name": coupon.program_id.name,
                    "points": "(%s)"
                    % coupon._format_points(wizard.order_id._get_real_points_for_coupon(coupon)),
                    "options": [
                        option
                        for reward in rewards.sorted("id")
                        for option in self._get_reward_options(coupon, reward)
                    ],
                }
                for coupon, rewards in claimable_rewards.items()
                if coupon not in wizard.applied_coupon_ids._origin
            ]

    @api.depends("selected_reward_ids", "selected_product_ids")
    def _compute_applied_reward_description(self):
        for wizard in self:
            names = []
            for reward in wizard.selected_reward_ids._origin:
                product = wizard._get_selected_product(reward) or reward.reward_product_ids[:1]
                names.append(self._get_reward_name(reward, product))
            wizard.applied_reward_description = " + ".join(names) or False

    def action_apply(self):
        self.ensure_one()
        if not self.selected_reward_ids:
            raise ValidationError(self.env._("No reward selected."))
        claimable_rewards = self.order_id._get_claimable_rewards()
        for reward in self.selected_reward_ids:
            coupon = next(
                (coupon for coupon, rewards in claimable_rewards.items() if reward in rewards), None
            )
            if not coupon:
                raise ValidationError(
                    self.env._(
                        "Coupon not found while trying to add the following reward: %s",
                        reward.description,
                    )
                )
            product = self._get_selected_product(reward)
            status = self.order_id._apply_program_reward(reward, coupon, product=product)
            if "error" in status:
                raise ValidationError(status["error"])
        self.order_id._update_programs_and_rewards()
        self._unlink_unused_coupon_ids()
        return True

    def action_cancel(self):
        self.ensure_one()
        self._unlink_unused_coupon_ids()

    def action_verify_coupon(self):
        self.ensure_one()
        if not self.order_id:
            raise ValidationError(self.env._("Invalid sales order."))
        status = self.order_id._try_apply_code(self.coupon_code)
        if "error" in status:
            raise ValidationError(status["error"])
        # Select the reward when there is no choice to make
        for coupon, rewards in status.items():
            options = [
                option for reward in rewards for option in self._get_reward_options(coupon, reward)
            ]
            if len(options) == 1:
                self.applied_coupon_ids |= coupon
                self.selected_reward_ids |= rewards
        action = self.env["ir.actions.actions"]._for_xml_id(
            "sale_loyalty.sale_loyalty_reward_wizard_action"
        )
        action["res_id"] = self.id
        return action

    def _get_selected_product(self, reward):
        """Return the product chosen for the reward if it lets choose among several products."""
        self.ensure_one()
        if not reward.multi_product:
            return self.env["product.product"]
        return (self.selected_product_ids._origin & reward.reward_product_ids)[:1]

    def _get_reward_options(self, coupon, reward):
        """Return the options to claim the reward with: one per product it lets choose from."""
        points = coupon._format_points(reward.required_points)
        return [
            {
                "reward_id": reward.id,
                # Only store the product to choose it, the reward gives it otherwise
                "product_id": reward.multi_product and product.id,
                "label": "%s (%s)" % (self._get_reward_name(reward, product), points),
            }
            for product in reward.reward_product_ids or [self.env["product.product"]]
        ]

    def _get_reward_name(self, reward, product):  # ruff: ignore[no-self-use]
        """Return the name of the reward, or only of its free product if it gives one."""
        if product:
            return product.with_context(display_default_code=False).display_name
        return reward.description

    def _unlink_unused_coupon_ids(self):
        reward_coupons = self.order_id.order_line.coupon_id
        self.order_id.coupon_point_ids.filtered(
            lambda points: (
                points.coupon_id.program_id.applies_on == "current"
                and points.coupon_id not in reward_coupons
            )
        ).coupon_id.sudo().unlink()
