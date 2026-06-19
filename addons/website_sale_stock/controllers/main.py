# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.exceptions import BadRequest

from odoo import _
from odoo.http import Controller, request, route
from odoo.tools.mail import email_re


class WebsiteSaleStock(Controller):

    @route('/shop/add/stock_notification', type='jsonrpc', auth='public', website=True)
    def add_stock_email_notification(self, email, product_id):
        # TDE FIXME: seems a bit open
        if not email_re.match(email):
            raise BadRequest(_("Invalid Email"))

        is_public = request.website.is_public_user()
        session_key = 'product_with_stock_notification_enabled'
        subscribed = set(request.session.get(session_key, []))
        pid = str(product_id)

        # block duplicates
        if pid in subscribed:
            raise BadRequest(_("You are already subscribed to notifications for this product."))

        # max 5 unique products per public session
        if is_public and len(subscribed) >= 5:
            raise BadRequest(_("You have reached the maximum number of stock notifications for this session."))

        # TODO: Integrate validation checks from PR #246236 here:
        # 1. Verify product exists and is valid for notifications
        # 2. Prevent public users from subscribing using an email tied to a registered account

        product = request.env['product.product'].browse(int(product_id))
        partner = request.env['mail.thread'].sudo()._partner_find_from_emails_single([email])

        if not product._has_stock_notification(partner):
            product.sudo().stock_notification_partner_ids += partner

        if request.website.is_public_user():
            request.session['product_with_stock_notification_enabled'] = list(
                set(request.session.get('product_with_stock_notification_enabled', []))
                | {pid}
            )
            request.session['stock_notification_email'] = email

        return {'success': True}
