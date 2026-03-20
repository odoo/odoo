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
