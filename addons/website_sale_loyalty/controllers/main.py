# -*- coding: utf-8 -*-
from odoo import http, _
from odoo.addons.website_sale.controllers import main
from odoo.exceptions import UserError, ValidationError
from odoo.http import request

from werkzeug.urls import url_encode, url_parse


class WebsiteSale(main.WebsiteSale):

    @http.route()
    def pricelist(self, promo, **post):
        order = request.website.sale_get_order()
        coupon_status = order._try_apply_code(promo)
        if coupon_status.get('not_found'):
            return super(WebsiteSale, self).pricelist(promo, **post)
        elif coupon_status.get('error'):
            request.session['error_promo_code'] = coupon_status['error']
        elif 'error' not in coupon_status:
            reward_successfully_applied = True
            if len(coupon_status) == 1:
                coupon, rewards = next(iter(coupon_status.items()))
                if len(rewards) == 1 and not rewards.multi_product:
                    reward_successfully_applied = self._apply_reward(order, rewards, coupon)

            if reward_successfully_applied:
                request.session['successful_code'] = promo
        return request.redirect(post.get('r', '/shop/cart'))

    @http.route()
    def shop_payment(self, **post):
        order = request.website.sale_get_order()
        if order:
            order._update_programs_and_rewards()
            order._auto_apply_rewards()
        return super(WebsiteSale, self).shop_payment(**post)

    @http.route(['/shop/cart'], type='http', auth="public", website=True)
    def cart(self, **post):
        order = request.website.sale_get_order()
        if order and order.state != 'draft':
            request.session['sale_order_id'] = None
            order = request.website.sale_get_order()
        if order:
            order._update_programs_and_rewards()
            order._auto_apply_rewards()

        res = super().cart(**post)

        # TODO in master: remove and pass delete=True to the methods fetching the error/success
        # messages in _get_website_sale_extra_values
        # clean session messages after displaying them
        if request.session.get('error_promo_code'):
            request.session.pop('error_promo_code')
        if request.session.get('successful_code'):
            request.session.pop('successful_code')

        return res

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
        if not coupon_id or not reward_id.exists():
            return request.redirect(redirect)
        if reward_id.multi_product and 'product_id' in post:
            request.update_context(product_id=int(post['product_id']))
        else:
            request.redirect(redirect)

        self._apply_reward(order, reward_id, coupon_id)
        return request.redirect(redirect)

    def _apply_reward(self, order, reward, coupon):
        """Try to apply the given program reward

        :returns: whether the reward was successfully applied
        :rtype: bool
        """
        product_id = request.env.context.get('product_id')
        product = product_id and request.env['product.product'].sudo().browse(product_id)
        try:
            reward_status = order._apply_program_reward(reward, coupon, product=product)
        except UserError as e:
            request.session['error_promo_code'] = str(e)
            return False
        if 'error' in reward_status:
            request.session['error_promo_code'] = reward_status['error']
            return False
        return True

    @http.route()
    def cart_update_json(self, *args, set_qty=None, **kwargs):
        # When a reward line is deleted we remove it from the auto claimable rewards
        if set_qty == 0:
            request.update_context(website_sale_loyalty_delete=True)
            # We need to update the website since `get_sale_order` is called on the website
            # and does not follow the request's context
            request.website = request.website.with_context(website_sale_loyalty_delete=True)
        return super().cart_update_json(*args, set_qty=set_qty, **kwargs)


class PaymentPortal(main.PaymentPortal):

    def _validate_transaction_for_order(self, transaction, sale_order_id):
        """Update programs & rewards before finalizing transaction.

        :param payment.transaction transaction: The payment transaction
        :param int order_id: The id of the sale order to pay
        :raise: ValidationError if the order amount changed after updating rewards
        """
        super()._validate_transaction_for_order(transaction, sale_order_id)
        order_sudo = request.env['sale.order'].sudo().browse(sale_order_id)
        if order_sudo.exists():
            initial_amount = order_sudo.amount_total
            order_sudo._update_programs_and_rewards()
            order_sudo.validate_taxes_on_sales_order()  # re-applies taxcloud taxes if necessary
            if order_sudo.currency_id.compare_amounts(initial_amount, order_sudo.amount_total):
                raise ValidationError(
                    _("Cannot process payment: applied reward was changed or has expired.")
                )
