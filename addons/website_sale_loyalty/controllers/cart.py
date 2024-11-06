# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request, route

from odoo.addons.website_sale.controllers.cart import Cart as WebsiteSaleCart


class Cart(WebsiteSaleCart):

    @route()
    def cart(self, **post):
        order = request.website.sale_get_order()
        if order and order.state != 'draft':
            request.session['sale_order_id'] = None
            order = request.website.sale_get_order()
        if order:
            order._update_programs_and_rewards()
            order._auto_apply_rewards()
        return super().cart(**post)

    @route()
    def update_cart(self, *args, quantity=None, **kwargs):
        # When a reward line is deleted we remove it from the auto claimable rewards
        if quantity == 0:
            request.update_context(website_sale_loyalty_delete=True)
            # We need to update the website since `get_sale_order` is called on the website
            # and does not follow the request's context
            request.website = request.website.with_context(website_sale_loyalty_delete=True)
        return super().update_cart(*args, quantity=quantity, **kwargs)
