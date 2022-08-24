# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.website_sale.controllers import main as website_sale_controller
from odoo.tools import email_re
from odoo import http, _
from odoo.http import request
from odoo.exceptions import ValidationError
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
    @http.route(['/shop/add/stock_notification'], type="json", auth="public", website=True)
    def add_stock_email_notification(self, email, product_id):
        if not email_re.match(email):
            raise BadRequest(_("Invalid Email"))

        product = request.env['product.product'].browse(int(product_id))
        partners = request.env['res.partner'].sudo()._mail_find_partner_from_emails([email], force_create=True)
        partner = partners[0]

        if not product._has_stock_notification(partner):
            product.sudo().stock_notification_partner_ids += partner

        if request.website.is_public_user():
            request.session['product_with_stock_notification_enabled'] = request.session.get(
                'product_with_stock_notification_enabled',
                set()
            ) | {product_id}
            request.session['stock_notification_email'] = email

    def _prepare_product_values(self, product, category='', search='', **kwargs):
        values = super()._prepare_product_values(product, category, search, **kwargs)
        # We need the user mail to prefill the back of stock notification, so we put it in the value that will be sent
        values['user_email'] = request.env.user.email or request.session.get('stock_notification_email', '')
        return values
