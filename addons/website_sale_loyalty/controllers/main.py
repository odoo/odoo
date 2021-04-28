# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http, _
from odoo.addons.website_sale.controllers import main
from odoo.http import request


class WebsiteSale(main.WebsiteSale):
    def _prepare_cart_values(self, request, values, **post):
        """ Publishes the available rewards to the cart view rendering """
        super()._prepare_cart_values(request, values, **post)
        if not post or post.get('type') != 'popover':
            order = request.website.sale_get_order()
            if request.website.loyalty_id and not request.website.is_public_user():
                values['available_rewards'] = request.website.loyalty_id.get_available_rewards(order)

    def _get_shop_payment_values(self, order, **kwargs):
        values = super()._get_shop_payment_values(order, **kwargs)
        order = request.website.sale_get_order()
        if order.available_loyalty_points < 0:
            values['errors'].append((
                _('Sorry, you do not have sufficient loyalty points for all rewards in your cart.'),
                _('Please remove some of the rewards before proceeding with check out.'),
            ))
        return values

    def checkout_form_validate(self, mode, all_form_values, data):
        order = request.website.sale_get_order()
        error, error_message = super().checkout_form_validate(mode, all_form_values, data)
        if order.available_loyalty_points < 0:
            error['order_line'] = 'error'
            error_message.append(_('Insufficient loyalty points: please remove some rewards.'))
        return error, error_message

    @http.route()
    def cart_update_json(self, product_id, line_id=None, add_qty=None, set_qty=None, display=True, **kw):
        """
        Overrides cart updates so that if the list of available rewards before the update is
        different from the one after the update, an empty response is returned which triggers a
        full refresh of the cart page, thus updating the display of the available rewards as well.
        """
        if not request.website.has_loyalty:
            return super().cart_update_json(product_id, line_id, add_qty, set_qty, display, **kw)
        order = request.website.sale_get_order()
        old_rewards = request.website.loyalty_id.get_available_rewards(order)
        result = super().cart_update_json(product_id, line_id, add_qty, set_qty, display, **kw)
        new_rewards = request.website.loyalty_id.get_available_rewards(order)
        if len(old_rewards) != len(new_rewards) or order.available_loyalty_points < 0:
            # upon receiving no cart_quantity, client refreshes the /shop/cart page
            return {}
        return result

    @http.route(['/shop/cart/update_reward'], type='http', auth="public", methods=['POST'], website=True)
    def cart_update_reward(self, reward_id, add_qty=1, **kw):
        """This route is called when adding a reward to cart."""
        sale_order = request.website.sale_get_order(force_create=True)
        reward = request.env['loyalty.reward'].browse(int(reward_id))
        if request.website.has_loyalty and reward in request.website.loyalty_id.get_available_rewards(sale_order):
            sale_order._cart_update_reward(
                reward_id=int(reward_id),
                add_qty=1,
            )
        return request.redirect("/shop/cart")
