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

        product = request.env['product.product'].browse(int(product_id))
        partner = request.env['mail.thread'].sudo()._partner_find_from_emails_single([email])

        if not product._has_stock_notification(partner):
            product.sudo().stock_notification_partner_ids += partner

        if request.website.is_public_user():
            request.session['product_with_stock_notification_enabled'] = list(
                set(request.session.get('product_with_stock_notification_enabled', []))
                | {product_id}
            )
            request.session['stock_notification_email'] = email
