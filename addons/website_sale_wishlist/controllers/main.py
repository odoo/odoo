# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo.http import Controller, request, route


class WebsiteSaleWishlist(Controller):

    @route('/shop/wishlist/add', type='json', auth='public', website=True)
    def add_to_wishlist(self, product_id, **kw):
        website = request.website
        pricelist = website.pricelist_id
        product = request.env['product.product'].browse(product_id)

        price = product._get_combination_info_variant()['price']

        Wishlist = request.env['product.wishlist']
        if request.website.is_public_user():
            Wishlist = Wishlist.sudo()
            partner_id = False
        else:
            partner_id = request.env.user.partner_id.id

        wish = Wishlist._add_to_wishlist(
            pricelist.id,
            pricelist.currency_id.id,
            request.website.id,
            price,
            product_id,
            partner_id
        )

        if not partner_id:
            request.session['wishlist_ids'] = request.session.get('wishlist_ids', []) + [wish.id]

        return wish

    @route('/shop/wishlist', type='http', auth='public', website=True, sitemap=False)
    def get_wishlist(self, count=False, **kw):
        wishes = request.env['product.wishlist'].with_context(display_default_code=False).current()
        if count:
            return request.make_response(json.dumps(wishes.product_id.ids))

        if not wishes:
            return request.redirect('/shop')

        return request.render(
            'website_sale_wishlist.product_wishlist',
            {
                'wishes': wishes,
            }
        )

    @route('/shop/wishlist/remove/<int:wish_id>', type='json', auth='public', website=True)
    def remove_from_wishlist(self, wish_id, **kw):
        wish = request.env['product.wishlist'].browse(wish_id)
        if request.website.is_public_user():
            wish_ids = request.session.get('wishlist_ids') or []
            if wish_id in wish_ids:
                request.session['wishlist_ids'].remove(wish_id)
                request.session.touch()
                wish.sudo().unlink()
        else:
            wish.unlink()
        return True
