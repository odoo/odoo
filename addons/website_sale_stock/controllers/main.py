# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.website_sale.controllers import main as website_sale_controller

from odoo import http
from odoo.http import request
from odoo.exceptions import ValidationError
from odoo.tools import email_re
from werkzeug.exceptions import BadRequest


class PaymentPortal(website_sale_controller.PaymentPortal):

    @http.route()
    def shop_payment_transaction(self, *args, **kwargs):
        """ Payment transaction override to double check cart quantities before
        placing the order
        """
        order = request.website.sale_get_order()
        values = []
        for line in order.order_line:
            if line.product_id.type == 'product' and not line.product_id.allow_out_of_stock_order:
                cart_qty, avl_qty = order._get_cart_and_free_qty(line=line)
                if cart_qty > avl_qty:
                    line._set_shop_warning_stock(cart_qty, max(avl_qty, 0))
                    values.append(line.shop_warning)
        if values:
            raise ValidationError(' '.join(values))
        return super().shop_payment_transaction(*args, **kwargs)


class WebsiteSale(website_sale_controller.WebsiteSale):
    @http.route(['/shop/add_stock_email_notification'], type="json", auth="public", website=True)
    def add_stock_email_notification(self, email, product_id, displayed_in_cart):
        if not email_re.match(email):
            return {'error': BadRequest("Invalid Email")}

        website = request.env['website'].get_current_website()
        pricelist = website.pricelist_id
        product_id = int(product_id)
        product = request.env['product.product'].browse(product_id)
        price = product._get_combination_info_variant(pricelist=website.pricelist_id)['price']

        Wishlist = request.env['product.wishlist']
        partner_ids = request.env['res.partner'].sudo()._mail_find_partner_from_emails([email], force_create=True)
        partner_id = partner_ids[0].id

        if request.website.is_public_user():
            Wishlist = Wishlist.sudo()

        wish = Wishlist.current().filtered_domain([('product_id', '=', product_id)])
        if not wish:
            wish = Wishlist._add_to_wishlist(pricelist.id, pricelist.currency_id.id, request.website.id, price, product_id, partner_id)
            request.session.setdefault('wishlist_ids', []).append(wish.id)
        wish.partner_id = partner_id
        wish.stock_notification = True
        wish.displayed_in_cart = displayed_in_cart

    def _prepare_product_values(self, product, category='', search='', **kwargs):
        values = super()._prepare_product_values(product, category, search, **kwargs)
        # We need the user mail to prefill the out of stock notification, so we put it in the value that will be sent
        # to the fronted
        values['email'] = request.env.user.email
        return values
