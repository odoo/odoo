from collections import defaultdict
from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Domain
from odoo.http import request
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    disabled_auto_rewards = fields.Many2many(
        comodel_name="loyalty.reward",
        relation="sale_order_disabled_auto_rewards_rel",
    )

    def _get_domain_program(self):
        res = super()._get_domain_program()
        if self.website_id:
            for idx, leaf in enumerate(res):
                if leaf[0] != "sale_ok":
                    continue
                res[idx] = ("ecommerce_ok", "=", True)
                return Domain.AND(
                    [res, [("website_id", "in", (self.website_id.id, False))]]
                )
        return res

    def _get_domain_trigger(self):
        res = super()._get_domain_trigger()
        if self.website_id:
            for idx, leaf in enumerate(res):
                if leaf[0] != "program_id.sale_ok":
                    continue
                res[idx] = ("program_id.ecommerce_ok", "=", True)
                return Domain.AND(
                    [
                        res,
                        [("program_id.website_id", "in", (self.website_id.id, False))],
                    ]
                )
        return res

    def _get_program_timezone(self):
        return self.website_id.salesperson_id.tz or super()._get_program_timezone()

    def _try_pending_coupon(self):
        if not request:
            _debug.logic("pending_coupon_skipped", reason="no_request")
            return False

        pending_coupon_code = request.session.get("pending_coupon_code")
        if pending_coupon_code:
            status = self._try_apply_code(pending_coupon_code)
            if "error" not in status:
                request.session.pop("pending_coupon_code")
                if len(status) == 1:
                    coupon, rewards = next(iter(status.items()))
                    if len(rewards) == 1 and not rewards.multi_product:
                        self._apply_program_reward(rewards, coupon)
            return status
        return True

    def _update_programs_and_rewards(self):
        for order in self:
            order._try_pending_coupon()
        return super()._update_programs_and_rewards()

    def _auto_apply_rewards(self):
        self.check_singleton()

        claimed_reward_count = 0
        claimable_rewards = self._get_claimable_rewards()
        for coupon, rewards in claimable_rewards.items():
            if (
                len(coupon.program_id.reward_ids) != 1
                or coupon.program_id.is_nominative
                or (rewards.reward_type == "product" and rewards.multi_product)
                or rewards in self.disabled_auto_rewards
                or rewards in self.line_ids.reward_id
            ):
                continue

            try:
                res = self._apply_program_reward(rewards, coupon)
                if "error" not in res:
                    claimed_reward_count += 1
            except UserError:
                pass

        return bool(claimed_reward_count)

    def _compute_website_order_line(self):
        super()._compute_website_order_line()
        for order in self:
            grouped_order_lines = defaultdict(lambda: self.env["sale.order.line"])
            for line in order.line_ids:
                if line.reward_id and line.coupon_id:
                    grouped_order_lines[
                        (line.reward_id, line.coupon_id, line.reward_identifier_code)
                    ] |= line
            new_lines = self.env["sale.order.line"]
            for lines in grouped_order_lines.values():
                if lines.reward_id.reward_type != "discount":
                    continue
                new_lines += self.env["sale.order.line"].new(
                    {
                        "product_id": lines[0].product_id.id,
                        "tax_ids": False,
                        "price_unit": sum(lines.mapped("price_unit")),
                        "price_subtotal": sum(lines.mapped("price_subtotal")),
                        "price_total": sum(lines.mapped("price_total")),
                        "discount": 0.0,
                        "name": lines[0].name_short
                        if lines.reward_id.reward_type != "product"
                        else lines[0].name,
                        "product_qty": 1,
                        "product_uom_id": lines[0].product_uom_id.id,
                        "order_id": order.id,
                        "is_reward_line": True,
                        "coupon_id": lines.coupon_id,
                        "reward_id": lines.reward_id,
                    }
                )
            if new_lines:
                order.website_order_line += new_lines

    def _compute_cart_info(self):
        super()._compute_cart_info()
        for order in self:
            reward_lines = order.website_order_line.filtered(
                lambda line: line.is_reward_line
            )
            order.cart_quantity -= int(sum(reward_lines.mapped("product_qty")))

    def get_promo_code_error(self, delete=True):
        error = request.session.get("error_promo_code")
        if error and delete:
            request.session.pop("error_promo_code")
        return error

    def get_promo_code_success_message(self, delete=True):
        if not request.session.get("successful_code"):
            return False
        code = request.session.get("successful_code")
        if delete:
            request.session.pop("successful_code")
        return code

    def _set_delivery_method(self, *args, **kwargs):
        super()._set_delivery_method(*args, **kwargs)
        self._update_programs_and_rewards()

    def _remove_delivery_line(self):
        super()._remove_delivery_line()
        self._update_programs_and_rewards()

    def _cart_update_order_line(self, order_line, quantity, **kwargs):
        if (
            quantity <= 0
            and order_line.coupon_id
            and order_line.reward_id
            and order_line.reward_id.reward_type == "discount"
        ):
            order_line = order_line.with_context(website_sale_loyalty_delete=True)

        return super()._cart_update_order_line(order_line, quantity, **kwargs)

    def _sync_cart_after_update(self):
        super()._sync_cart_after_update()
        self._update_programs_and_rewards()
        self._auto_apply_rewards()
        if request:
            request.session["website_sale_cart_quantity"] = self.cart_quantity

    def _get_non_delivery_lines(self):
        return super()._get_non_delivery_lines() - self._get_free_shipping_lines()

    def _get_free_shipping_lines(self):
        self.check_singleton()
        return self.line_ids.filtered(lambda l: l.reward_id.reward_type == "shipping")

    def _allow_nominative_programs(self):
        if not request or not hasattr(request, "website"):
            return super()._allow_nominative_programs()
        return (
            not request.website.is_public_user()
            and super()._allow_nominative_programs()
        )

    @api.autovacuum
    def _gc_abandoned_coupons(self, *args, **kwargs):
        ICP = self.env["ir.config_parameter"]
        validity = ICP.get_param("website_sale_coupon.abandonned_coupon_validity", 4)
        validity = fields.Datetime.to_string(
            fields.Datetime.now() - timedelta(days=int(validity))
        )
        so_to_reset = self.env["sale.order"].search(
            [
                ("state", "=", "draft"),
                ("write_date", "<", validity),
                ("website_id", "!=", False),
                ("applied_coupon_ids", "!=", False),
            ]
        )
        so_to_reset.applied_coupon_ids = False
        for so in so_to_reset:
            so._update_programs_and_rewards()

    def _get_claimable_and_showable_rewards(self):
        self.check_singleton()
        res = self._get_claimable_rewards()
        loyality_cards = self.env["loyalty.card"].search(
            [
                ("partner_id", "=", self.partner_id.id),
                ("program_id", "any", self._get_domain_program()),
                "|",
                ("program_id.trigger", "=", "with_code"),
                "&",
                ("program_id.trigger", "=", "auto"),
                ("program_id.applies_on", "=", "future"),
            ]
        )
        total_is_zero = self.currency_id.is_zero(self.amount_total)
        global_discount_reward = self._get_applied_global_discount()
        for coupon in loyality_cards:
            points = self._get_real_points_for_coupon(coupon)
            for reward in coupon.program_id.reward_ids - self.line_ids.reward_id:
                if (
                    reward.is_global_discount
                    and global_discount_reward
                    and self._best_global_discount_already_applied(
                        global_discount_reward, reward
                    )
                ):
                    continue
                if reward.reward_type == "discount" and total_is_zero:
                    continue
                if (
                    coupon.expiration_date
                    and coupon.expiration_date < fields.Date.today()
                ):
                    continue
                if points >= reward.required_points:
                    if coupon in res:
                        res[coupon] |= reward
                    else:
                        res[coupon] = reward
        return res

    def _cart_find_product_line(self, *args, **kwargs):
        return (
            super()
            ._cart_find_product_line(*args, **kwargs)
            .filtered(lambda sol: not sol.is_reward_line)
        )

    def _recompute_cart(self):
        self._update_programs_and_rewards()
        self._auto_apply_rewards()
        super()._recompute_cart()
