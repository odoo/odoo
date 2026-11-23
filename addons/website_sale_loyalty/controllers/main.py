# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.urls import url_encode, url_parse

from odoo.exceptions import UserError
from odoo.http import request, route

from odoo.addons.payment import utils as payment_utils
from odoo.addons.website_sale.controllers import main


class WebsiteSale(main.WebsiteSale):
    @route()
    def pricelist_apply(self, promo, reward_id=None, **post):
        result = {}

        if not (order_sudo := request.cart):
            return {"success": False}
        coupon_status = order_sudo._try_apply_code(promo)
        if coupon_status.get("not_found"):
            return super().pricelist_apply(promo, **post)
        if coupon_status.get("error"):
            result.update({"success": False, "message": coupon_status["error"]})
        elif "error" not in coupon_status:
            if len(coupon_status) == 1:
                coupon, rewards = next(iter(coupon_status.items()))
                if len(rewards) == 1:
                    reward = rewards
                else:
                    reward = reward_id in rewards.ids and rewards.browse(reward_id)
                if reward and (not reward.multi_product or self.env.context.get("product_id")):
                    reward_status = self._apply_reward(order_sudo, reward, coupon)
                    if not reward_status["success"]:
                        return reward_status

            # refresh rewards
            order_sudo._update_programs_and_rewards()
            order_sudo._auto_apply_rewards()
            result.update({
                "success": True,
                "message": self.env._(
                    "You have successfully applied the following code: %(code)s.", code=promo
                ),
            })
        return result

    def _promo_code_unavailable_warning(self):
        return self.env._("Invalid or expired promo code.")

    @route(["/coupon/<string:code>"], type="http", auth="public", website=True, sitemap=False)
    def activate_coupon(self, code, r="/shop", **_kwargs):
        url_parts = url_parse(r)
        url_query = url_parts.decode_query()
        url_query.pop("coupon_error", False)  # trust only Odoo error message
        url_query.pop("coupon_error_type", False)
        code = code.strip()

        request.session["pending_coupon_code"] = code
        if order_sudo := request.cart:
            result = order_sudo._try_pending_coupon()
            if isinstance(result, dict) and "error" in result:
                url_query["coupon_error"] = result["error"]
            else:
                url_query["notify_coupon"] = code
        else:
            url_query["coupon_error"] = self.env._(
                "The coupon will be automatically applied when you add something in your cart."
            )
            url_query["coupon_error_type"] = "warning"
        redirect = url_parts.replace(query=url_encode(url_query))
        return request.redirect(redirect.to_url())

    @route("/shop/claimreward", type="jsonrpc", auth="public", website=True, sitemap=False)
    def claim_reward(self, reward_id, code=None, product_id=None, **_post):
        if not (order_sudo := request.cart):
            return {"success": False}

        try:
            reward_id = int(reward_id)
        except ValueError:
            reward_id = None

        reward_sudo = self.env["loyalty.reward"].sudo().browse(reward_id).exists()
        if not reward_sudo:
            return {"success": False}

        if reward_sudo.multi_product and product_id:
            request.update_context(product_id=int(product_id))

        program_sudo = reward_sudo.program_id
        claimable_rewards = order_sudo._get_claimable_and_showable_rewards()
        coupon = self.env["loyalty.card"]
        for coupon_, rewards in claimable_rewards.items():
            if reward_sudo in rewards:
                coupon = coupon_
                if code == coupon.code and (
                    (
                        program_sudo.trigger == "with_code"
                        and program_sudo.program_type != "promo_code"
                    )
                    or (
                        program_sudo.trigger == "auto"
                        and program_sudo.applies_on == "future"
                        and program_sudo.program_type not in ("ewallet", "loyalty")
                    )
                ):
                    result = self.pricelist_apply(code, reward_id=reward_id)
                    return self._add_cart_amount(order_sudo, result)
        if coupon:
            result = self._apply_reward(order_sudo, reward_sudo, coupon)
            return self._add_cart_amount(order_sudo, result)
        return {"success": False}

    def _add_cart_amount(self, order_sudo, result):
        """Add the new amount of the order to the result of a successful reward claim.

        :param sale.order order_sudo: The current cart.
        :param dict result: The result of the reward claim.
        :return: The result, with the `amount` and `minor_amount` of the order if successful.
        :rtype: dict
        """
        if result.get("success"):
            result.update({
                "amount": order_sudo.amount_total,
                "minor_amount": (
                    order_sudo.amount_total
                    and payment_utils.to_minor_currency_units(
                        order_sudo.amount_total, order_sudo.currency_id
                    )
                ),
            })
        return result

    def _apply_reward(self, order, reward, coupon):
        """Try to apply the given program reward.

        :return: The status of the application, in the format
                 {'success': bool, 'message': str}, with a message only if it failed.
        :rtype: dict
        """
        product_id = self.env.context.get("product_id")
        product = product_id and self.env["product.product"].sudo().browse(product_id)
        try:
            reward_status = order._apply_program_reward(reward, coupon, product=product)
        except UserError as e:
            return {"success": False, "message": str(e)}
        if "error" in reward_status:
            return {"success": False, "message": reward_status["error"]}
        order._update_programs_and_rewards()
        if order.carrier_id.free_over and not reward.program_id.is_payment_program:
            # update shipping cost if it's `free_over` and reward isn't eWallet or gift card
            # will call `_update_programs_and_rewards` again, updating applied eWallet/gift cards
            res = order.carrier_id.rate_shipment(order)
            if res.get("success"):
                order.set_delivery_line(order.carrier_id, res["price"])
            else:
                order._remove_delivery_line()
        return {"success": True}
