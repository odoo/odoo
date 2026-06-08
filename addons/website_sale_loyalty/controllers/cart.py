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

    def _cart_values(self, **post):
        values = super()._cart_values(**post)
        if order_sudo := request.cart:
            values["promotion_progress_bars"] = order_sudo._get_promotion_progress_bars()
        return values

    def _total_values(self):
        values = super()._total_values()
        if order_sudo := request.cart:
            values["promotion_progress_bars"] = order_sudo._get_promotion_progress_bars()
        return values

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
