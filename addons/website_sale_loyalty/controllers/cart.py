# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request, route

from odoo.addons.website_sale.controllers.cart import Cart as WebsiteSaleCart


class Cart(WebsiteSaleCart):
    @route()
    def cart(self, **post):
        if order_sudo := request.cart:
            order_sudo._update_programs_and_rewards()
            order_sudo._auto_apply_rewards()
        return super().cart(**post)

    @route("/wallet/top_up", type="http", auth="user", website=True, sitemap=False)
    def wallet_top_up(self, **kwargs):
        product = self.env["product.product"].browse(int(kwargs["trigger_product_id"]))
        self.add_to_cart(product.product_tmpl_id.id, product.id, 1)
        return request.redirect("/shop/cart")

    @route()
    def add_to_cart(self, *args, **kwargs):
        applied_before = (
            {p.id for p in request.cart._get_applied_programs()} if request.cart else set()
        )

        result = super().add_to_cart(*args, **kwargs)

        order_sudo = request.cart
        if order_sudo:
            bars = [
                bar
                for bar in order_sudo._get_promotion_progress_bars()
                if bar["progress"] < 100 or bar["program_id"] not in applied_before
            ]
            if bars:
                for notif in result.get("notifications", []):
                    if notif["type"] == "item_added":
                        notif["data"]["promotion_progress_bars"] = bars
                        break
        return result

    def _prepare_cart_line_data(self, line):
        line_data = super()._prepare_cart_line_data(line)
        return self._add_reward_line_data(line_data, line)

    def _prepare_cart_summary_line_data(self, line):
        line_data = super()._prepare_cart_summary_line_data(line)
        return self._add_reward_line_data(line_data, line)

    def _add_reward_line_data(self, line_data, line):
        show_coupon_code = (
            line.coupon_id
            and line.order_id != line.coupon_id.order_id
            and not line.coupon_id.program_id.is_nominative
        )
        line_data.update({
            "is_reward_line": line.is_reward_line,
            "show_coupon_code": show_coupon_code,
            **(
                {
                    "coupon_code": line.coupon_id.code,
                    "coupon_expiration_date": line.coupon_id.expiration_date,
                }
                if show_coupon_code
                else {}
            ),
            **({"reward_type": line.reward_id.reward_type} if line.is_reward_line else {}),
        })
        return line_data

    @route()
    def cart_totals(self, order_id):
        cart_totals = super().cart_totals(order_id)
        if order_sudo := request.cart:
            cart_totals["promotion_progress_bars"] = order_sudo._get_promotion_progress_bars()
            cart_totals["cart_rewards"] = self._cart_rewards()

        return cart_totals

    def _cart_rewards(self):
        order_sudo = request.cart

        rewards_by_coupon = order_sudo._get_claimable_and_showable_rewards()
        cart_rewards = []
        for coupon, rewards in rewards_by_coupon.items():
            points = order_sudo._get_real_points_for_coupon(coupon)
            formatted_points = coupon._format_points(points)
            is_loyalty = rewards[0].program_id.program_type == "loyalty"
            reward_data = []
            for reward in rewards:
                program = reward.program_id
                show_code_details = program.program_type not in {
                    "ewallet",
                    "promo_code",
                    "loyalty",
                } and (
                    program.trigger == "with_code"
                    or (program.trigger == "auto" and program.applies_on == "future")
                )
                reward_data.append({
                    "id": reward.id,
                    "description": reward.description,
                    "program_type": program.program_type,
                    "program_trigger": program.trigger,
                    "program_applies_on": program.applies_on,
                    "portal_visible": program.portal_visible,
                    "is_nominative": program.is_nominative,
                    "required_points": reward.required_points,
                    "formatted_required_points": coupon._format_points(reward.required_points),
                    "formatted_points": formatted_points,
                    "button_label": (
                        request.env._("Use")
                        if (
                            (
                                program.trigger == "with_code"
                                and program.program_type != "promo_code"
                            )
                            or (program.trigger == "auto" and program.applies_on == "future")
                        )
                        else request.env._("Claim")
                    ),
                    "show_points": (
                        program.portal_visible
                        and not program.is_nominative
                        and not show_code_details
                    ),
                    "show_required_points": (
                        program.portal_visible
                        and program.is_nominative
                        and program.program_type != "ewallet"
                        and not show_code_details
                    ),
                    "show_code_details": show_code_details,
                    "show_ewallet_points": program.program_type == "ewallet",
                    "multi_product": reward.multi_product,
                    "products": [
                        {"id": product.id, "display_name": product.display_name}
                        for product in reward.reward_product_ids
                    ]
                    if reward.multi_product
                    else [],
                })
            cart_rewards.append({
                "coupon_id": coupon.id,
                "coupon_code": coupon.code,
                "coupon_code_display": (
                    coupon.code[-4:].rjust(14, "★")
                    if coupon and not coupon.program_id.is_nominative
                    else False
                ),
                "coupon_expiration_date": coupon.expiration_date or False,
                "point_name": coupon.point_name,
                "points": points,
                "formatted_points": formatted_points,
                "is_loyalty": is_loyalty,
                "rewards": reward_data,
            })
        return cart_rewards
