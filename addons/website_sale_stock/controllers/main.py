# Part of Odoo. See LICENSE file for full copyright and licensing details.

<<<<<<< bab1f256eaec4c3e1a44b2bcb557d18ab2c38e5d
from werkzeug.exceptions import BadRequest
||||||| 1c60defdfedd4de11a18da63bec97f4c61a5dc81
from odoo.addons.website_sale.controllers import main as website_sale_controller
from odoo.tools import email_re
from odoo import http, _
from odoo.http import request
from werkzeug.exceptions import BadRequest
=======
from odoo.addons.website_sale.controllers import main as website_sale_controller
from odoo.tools import email_re
from odoo import http, _
from odoo.http import request
from odoo.exceptions import AccessError, ValidationError
>>>>>>> c574855859d9a874dbd5d803da328300c6ffe300

from odoo import _
from odoo.http import Controller, request, route
from odoo.tools.mail import email_re


class WebsiteSaleStock(Controller):

    @route('/shop/add/stock_notification', type='json', auth='public', website=True)
    def add_stock_email_notification(self, email, product_id):
        if not email_re.match(email):
            raise ValidationError(_("Invalid Email"))

        product = request.env['product.product'].browse(int(product_id))

        # check if product available
        if not product.exists() or not product._can_add_to_stock_notifications():
            raise ValidationError(_("This product is not eligible for stock notifications."))

        partners = request.env['res.partner'].sudo()._mail_find_partner_from_emails([email], force_create=True)
        partner = partners[0]

        is_public_user = request.website.is_public_user()
        if is_public_user and partner.user_ids.exists():
            raise AccessError(_("Please sign in to proceed."))

        if not product._has_stock_notification(partner):
            product.sudo().stock_notification_partner_ids += partner

<<<<<<< bab1f256eaec4c3e1a44b2bcb557d18ab2c38e5d
        if request.website.is_public_user():
            request.session['product_with_stock_notification_enabled'] = list(
                set(request.session.get('product_with_stock_notification_enabled', []))
                | {product_id}
            )
||||||| 1c60defdfedd4de11a18da63bec97f4c61a5dc81
        if request.website.is_public_user():
            request.session['product_with_stock_notification_enabled'] = request.session.get(
                'product_with_stock_notification_enabled',
                set()
            ) | {product_id}
=======
        if is_public_user:
            request.session['product_with_stock_notification_enabled'] = request.session.get(
                'product_with_stock_notification_enabled',
                set()
            ) | {product_id}
>>>>>>> c574855859d9a874dbd5d803da328300c6ffe300
            request.session['stock_notification_email'] = email
