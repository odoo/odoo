# Part of Odoo. See LICENSE file for full copyright and licensing details.

from urllib.parse import parse_qs, urlencode, urlsplit

from odoo.http import request, route
from odoo.http.stream import content_disposition
from odoo.tools.translate import LazyTranslate

from odoo.addons.payment.controllers import portal as payment_portal
from odoo.addons.website_sale.const import SHOP_PATH

_lt = LazyTranslate(__name__)


class Confirmation(payment_portal.PaymentPortal):
    def _prepare_shop_payment_confirmation_values(self, order):
        """Prepare the dict containing the values to be rendered by the confirmation template.
        This method is called in the payment process route.
        """
        rendering_values = {
            "order": order,
            "website_sale_order": order,
            "order_tracking_info": (
                order._get_purchase_tracking_info() if self.env.website.google_analytics_key else {}
            ),
        }
        if (
            self.env["res.users"]._get_signup_invitation_scope() == "b2c"
            and self.env.website.is_public_user()
        ):
            order.partner_id.signup_prepare()
            signup_url = urlsplit(
                order.partner_id.with_context(relative_url=True)._get_signup_url()
            )

            rendering_values["signup_url"] = signup_url._replace(
                query=urlencode(
                    dict(parse_qs(signup_url.query), redirect="/shop/unarchive_user_addresses"),
                    doseq=True,
                )
            ).geturl()

        return rendering_values

    @route(
        ["/shop/confirmation"],
        type="http",
        auth="public",
        website=True,
        sitemap=False,
        list_as_website_content=_lt("Shop Confirmation"),
    )
    def shop_payment_confirmation(self, **_post):
        """End of checkout process controller. Confirmation is basically seing
        the status of a sale.order. State at this point:
         - should not have any context / session info: clean them
         - take a sale.order id, because we request a sale.order and are not
           session dependant anymore.
        """
        sale_order_id = request.session.get("sale_last_order_id")
        if sale_order_id:
            order = self.env["sale.order"].sudo().browse(sale_order_id)
            values = self._prepare_shop_payment_confirmation_values(order)
            return request.render("website_sale.confirmation", values)
        return request.redirect(SHOP_PATH)

    @route("/shop/unarchive_user_addresses", type="http", auth="user", sitemap=False)
    def shop_unarchive_user_addresses(self):
        self.env["res.partner"].sudo().search([
            ("active", "=", False),
            ("parent_id", "=", self.env.user.partner_id.id),
        ]).active = True

        return request.redirect("/my")

    @route(["/shop/print"], type="http", auth="public", website=True, sitemap=False)
    def print_saleorder(self, **_kwargs):
        sale_order_id = request.session.get("sale_last_order_id")
        if sale_order_id:
            sale_order = self.env["sale.order"].sudo().browse(sale_order_id)
            filename = f"Order - {sale_order.name}"
            pdf, _ = (
                self
                .env["ir.actions.report"]
                .sudo()
                ._render_qweb_pdf("sale.action_report_saleorder", [sale_order_id])
            )
            pdfhttpheaders = [
                ("Content-Type", "application/pdf"),
                ("Content-Length", "%s" % len(pdf)),
                ("Content-Disposition", content_disposition(filename, "inline")),
            ]
            return request.make_response(pdf, headers=pdfhttpheaders)
        return request.redirect(SHOP_PATH)

    @route(["/shop/print/invoice"], type="http", auth="public", website=True, sitemap=False)
    def print_invoice(self, **_kwargs):
        sale_order_id = request.session.get("sale_last_order_id")
        if sale_order_id:
            sale_order = self.env["sale.order"].sudo().browse(sale_order_id)
            invoice = sale_order.invoice_ids and sale_order.invoice_ids[0]
            if invoice:
                pdf, _ = (
                    self
                    .env["ir.actions.report"]
                    .sudo()
                    ._render_qweb_pdf("account.account_invoices", [invoice.id])
                )
                filename = "%s.pdf" % (invoice.name or "Invoice")
                pdfhttpheaders = [
                    ("Content-Type", "application/pdf"),
                    ("Content-Length", "%s" % len(pdf)),
                    ("Content-Disposition", content_disposition(filename, "inline")),
                ]
                return request.make_response(pdf, headers=pdfhttpheaders)
        return request.redirect(SHOP_PATH)
