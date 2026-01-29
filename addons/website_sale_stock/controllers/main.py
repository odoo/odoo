# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.website_sale.controllers import main as website_sale_controller
from odoo.tools import email_re
from odoo import http, _
from odoo.http import request
from odoo.exceptions import AccessError, ValidationError


class WebsiteSale(website_sale_controller.WebsiteSale):
    @http.route(['/shop/add/stock_notification'], type="json", auth="public", website=True)
    def add_stock_email_notification(self, email, product_id):
        if not email_re.match(email):
            raise ValidationError(_("Invalid Email"))

        is_public_user = request.website.is_public_user()
        product = request.env['product.product'].browse(int(product_id))

        # check if product available
        if not product.exists() or not product._is_add_to_cart_allowed():
            raise ValidationError(_("The given product does not exist."))

        partners = request.env['res.partner'].sudo()._mail_find_partner_from_emails([email], force_create=True)
        partner = partners[0]

        if is_public_user and partner.user_ids.exists():
            raise AccessError(_("Please sign in to proceed, then try again."))

        if not product._has_stock_notification(partner):
            product.sudo().stock_notification_partner_ids += partner

        if is_public_user:
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

class CustomerPortal(website_sale_controller.CustomerPortal):
    def _sale_reorder_get_line_context(self):
        return {
            **super()._sale_reorder_get_line_context(),
            'website_sale_stock_get_quantity': True,
        }
