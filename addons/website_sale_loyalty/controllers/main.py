# -*- coding: utf-8 -*-
from odoo import http, _
from odoo.addons.website_sale.controllers import main
from odoo.exceptions import UserError
from odoo.http import request

from werkzeug.urls import url_encode, url_parse


class WebsiteSale(main.WebsiteSale):

    @http.route()
    def pricelist(self, promo, **post):
        order = request.website.sale_get_order()
        coupon_status = order._try_apply_code(promo)
        if 'error' not in coupon_status:
            if len(coupon_status) == 1:
                coupon, rewards = next(iter(coupon_status.items()))
                if len(rewards) == 1 and not rewards.multi_product:
                    self._apply_reward(order, rewards, coupon)
        if coupon_status.get('not_found'):
            return super(WebsiteSale, self).pricelist(promo, **post)
        elif coupon_status.get('error'):
            request.session['error_promo_code'] = coupon_status['error']
        if 'error' not in coupon_status:
            request.session['successful_code'] = promo
        return request.redirect(post.get('r', '/shop/cart'))

    @http.route()
    def shop_payment(self, **post):
        order = request.website.sale_get_order()
        res = super(WebsiteSale, self).shop_payment(**post)
        if order:
            order._update_programs_and_rewards()
            order._auto_apply_rewards()
        return res

    @http.route(['/shop/cart'], type='http', auth="public", website=True)
    def cart(self, **post):
        order = request.website.sale_get_order()
        if order:
            order._update_programs_and_rewards()
            order._auto_apply_rewards()
        return super(WebsiteSale, self).cart(**post)

    @http.route(['/coupon/<string:code>'], type='http', auth='public', website=True, sitemap=False)
    def activate_coupon(self, code, r='/shop', **kw):
        url_parts = url_parse(r)
        url_query = url_parts.decode_query()
        url_query.pop('coupon_error', False)  # trust only Odoo error message
        url_query.pop('coupon_error_type', False)
        code = code.strip()

        request.session['pending_coupon_code'] = code
        order = request.website.sale_get_order()
        if order:
            result = order._try_pending_coupon()
            if isinstance(result, dict) and 'error' in result:
                url_query['coupon_error'] = result['error']
            else:
                url_query['notify_coupon'] = code
        else:
            url_query['coupon_error'] = _("The coupon will be automatically applied when you add something in your cart.")
            url_query['coupon_error_type'] = 'warning'
        redirect = url_parts.replace(query=url_encode(url_query))
        return request.redirect(redirect.to_url())

    @http.route(['/shop/claimreward'], type='http', auth='public', website=True, sitemap=False)
    def claim_reward(self, reward, **post):
        order = request.website.sale_get_order()
        coupon_id = False
        try:
            reward_id = request.env['loyalty.reward'].sudo().browse(int(reward))
        except ValueError:
            reward_id = request.env['loyalty.reward'].sudo()
        claimable_rewards = order._get_claimable_rewards()
        for coupon, rewards in claimable_rewards.items():
            if reward_id in rewards:
                coupon_id = coupon
        redirect = post.get('r', '/shop/cart')
        if not coupon_id or not reward_id.exists() or reward_id.multi_product:
            return request.redirect(redirect)
        self._apply_reward(order, reward_id, coupon_id)
        return request.redirect(redirect)

    def _apply_reward(self, order, reward, coupon):
        try:
            order._apply_program_reward(reward, coupon)
        except UserError as e:
            request.session['error_promo_code'] = str(e)

    @http.route()
    def cart_update_json(self, *args, set_qty=None, **kwargs):
        # When a reward line is deleted we remove it from the auto claimable rewards
        if set_qty == 0:
            request.update_context(website_sale_loyalty_delete=True)
            # We need to update the website since `get_sale_order` is called on the website
            # and does not follow the request's context
            request.website = request.website.with_context(website_sale_loyalty_delete=True)
        return super().cart_update_json(*args, set_qty=set_qty, **kwargs)
