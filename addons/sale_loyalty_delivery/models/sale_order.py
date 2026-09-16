from odoo import _, models
from odoo.fields import Command
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _get_amount_total_without_delivery(self):
        res = super()._get_amount_total_without_delivery()
        return res - sum(
            self.line_ids.filtered(
                lambda l: (
                    l.coupon_id and l.coupon_id.program_type in ["ewallet", "gift_card"]
                )
            ).mapped("price_unit")
        )

    def set_delivery_line(self, carrier, amount):
        res = super().set_delivery_line(carrier, amount)
        for order in self:
            if any(line.reward_id.reward_type == "shipping" for line in order.line_ids):
                _debug.pipeline("free_shipping_reward_revalued", order=order)
                order._update_programs_and_rewards()
        return res

    def _get_no_effect_on_threshold_lines(self):
        res = super()._get_no_effect_on_threshold_lines()
        return res + self.line_ids.filtered(
            lambda line: line.is_delivery or line.reward_id.reward_type == "shipping"
        )

    def _get_not_rewarded_order_lines(self):
        order_line = super()._get_not_rewarded_order_lines()
        return order_line.filtered(lambda line: not line.is_delivery)

    def _get_reward_values_free_shipping(self, reward, coupon, **kwargs):
        delivery_line = self.line_ids.filtered(lambda l: l.is_delivery)[:1]
        _debug.logic(
            "free_shipping_reward",
            order=self,
            reward=reward,
            delivery_line=delivery_line,
        )
        taxes = delivery_line.product_id.taxes_id._filter_taxes_by_company(
            self.company_id
        )
        taxes = self.fiscal_position_id.map_tax(taxes)
        max_discount = reward.discount_max_amount or float("inf")
        return [
            {
                "name": _("Free Shipping - %s", reward.description),
                "reward_id": reward.id,
                "coupon_id": coupon.id,
                "points_cost": reward.required_points
                if not reward.clear_wallet
                else self._get_real_points_for_coupon(coupon),
                "product_id": reward.discount_line_product_id.id,
                "price_unit": -min(max_discount, delivery_line.price_unit or 0),
                "product_qty": 1,
                "order_id": self.id,
                "is_reward_line": True,
                "sequence": max(
                    self.line_ids.filtered(lambda x: not x.is_reward_line).mapped(
                        "sequence"
                    ),
                    default=0,
                )
                + 1,
                "tax_ids": [Command.clear()] + [Command.link(tax.id) for tax in taxes],
            }
        ]

    def _get_reward_line_values(self, reward, coupon, **kwargs):
        self.check_singleton()
        if reward.reward_type == "shipping":
            _debug.logic("reward_line_values", order=self, by="free_shipping")
            self = self.with_context(lang=self._get_lang())
            reward = reward.with_context(lang=self._get_lang())
            return self._get_reward_values_free_shipping(reward, coupon, **kwargs)
        return super()._get_reward_line_values(reward, coupon, **kwargs)

    def _get_claimable_rewards(self, forced_coupons=None):
        res = super()._get_claimable_rewards(forced_coupons)
        if any(reward.reward_type == "shipping" for reward in self.line_ids.reward_id):
            filtered_res = {}
            for coupon, rewards in res.items():
                filtered_rewards = rewards.filtered(
                    lambda r: r.reward_type != "shipping"
                )
                if filtered_rewards:
                    filtered_res[coupon] = filtered_rewards
            _debug.logic(
                "shipping_rewards_hidden", order=self, remaining=len(filtered_res)
            )
            res = filtered_res
        return res
