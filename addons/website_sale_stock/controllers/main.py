from werkzeug.exceptions import BadRequest

from odoo import _
from odoo.http import Controller, request, route
from odoo.libs.debug_log import DebugLog
from odoo.tools.mail import email_re

_debug = DebugLog(__name__)


class WebsiteSaleStock(Controller):
    @route("/shop/add/stock_notification", type="jsonrpc", auth="public", website=True)
    def add_stock_email_notification(self, email, product_id):
        if not email_re.match(email):
            _debug.logic(
                "stock_notification_refused", reason="bad_email", product=product_id
            )
            raise BadRequest(_("Invalid Email"))

        product = request.env["product.product"].browse(int(product_id))
        partner = (
            request.env["mixin.mail.thread"]
            .sudo()
            ._partner_get_or_create_from_emails_single([email])
        )

        if not product._has_stock_notification(partner):
            product.sudo().stock_notification_partner_ids += partner

        if request.website.is_public_user():
            request.session["product_with_stock_notification_enabled"] = list(
                set(request.session.get("product_with_stock_notification_enabled", []))
                | {product_id}
            )
            request.session["stock_notification_email"] = email
