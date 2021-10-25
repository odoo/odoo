# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http

from odoo.tools import single_email_re
from odoo.http import request
from odoo.addons.website_sale.controllers.main import WebsiteSale


class WebsiteSaleStockWishlist(WebsiteSale):
    @http.route(['/shop/wishlist/notify/<model("product.wishlist"):wish>'], type='json', auth="public", website=True)
    def notify_stock(self, wish, notify=True, **kw):
        if not request.website.is_public_user():
            wish.stock_notification = notify
        else:
            if "public_email_address" not in kw or not single_email_re.match(kw['public_email_address']):
                notify = not notify
            else:
                partner = request.env['res.partner'].sudo().find_or_create(kw['public_email_address'], assert_valid_email=False)
                wish.sudo().write({
                    'partner_id': partner,
                    'stock_notification': notify
                })
        return notify
