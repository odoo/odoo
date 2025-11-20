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

    @route('/wallet/top_up', type='http', auth='user', website=True, sitemap=False)
    def wallet_top_up(self, **kwargs):
        product = self.env['product.product'].browse(int(kwargs['trigger_product_id']))
        self.add_to_cart(product.product_tmpl_id.id, product.id, 1)
        return request.redirect('/shop/cart')

    def _cart_line_data(self, line):
        line_data = super()._cart_line_data(line)
        line_data['is_reward_line'] = line.is_reward_line
        line_data['show_coupon_code'] = (
            line.coupon_id
            if line.order_id != line.coupon_id.order_id
            and not line.coupon_id.program_id.is_nominative
            else False
        )

        if line_data['show_coupon_code']:
            line_data['coupon_code'] = line.coupon_id.code
            line_data['coupon_expiration_date'] = line.coupon_id.expiration_date

        if line_data['is_reward_line']:
            line_data['reward_type'] = line.reward_id.reward_type

        return line_data
