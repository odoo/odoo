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

    def _get_last_order(self):
        """Return the last order placed in this session (sudo'd), or an empty recordset.

        :rtype: sale.order
        """
        sale_order_id = request.session.get("sale_last_order_id")
        if not sale_order_id:
            return self.env["sale.order"]
        return self.env["sale.order"].sudo().browse(sale_order_id)

    def _render_pdf_response(self, report_ref, record_id, filename):
        """Render `report_ref` for `record_id` as a downloadable PDF HTTP response.

        :param str report_ref: The XML id of the `ir.actions.report` to render.
        :param int record_id: The id of the record to render the report for.
        :param str filename: The filename to give to the downloaded PDF.
        :rtype: werkzeug.wrappers.Response
        """
        pdf, _ = self.env["ir.actions.report"].sudo()._render_qweb_pdf(report_ref, [record_id])
        headers = [
            ("Content-Type", "application/pdf"),
            ("Content-Length", "%s" % len(pdf)),
            ("Content-Disposition", content_disposition(filename, "inline")),
        ]
        return request.make_response(pdf, headers=headers)

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
        order = self._get_last_order()
        if not order:
            return request.redirect(SHOP_PATH)
        values = self._prepare_shop_payment_confirmation_values(order)
        return request.render("website_sale.confirmation", values)

    @route("/shop/unarchive_user_addresses", type="http", auth="user", sitemap=False)
    def shop_unarchive_user_addresses(self):
        self.env["res.partner"].sudo().search([
            ("active", "=", False),
            ("parent_id", "=", self.env.user.partner_id.id),
        ]).active = True

        return request.redirect("/my")

    @route(["/shop/print"], type="http", auth="public", website=True, sitemap=False)
    def print_saleorder(self, **_kwargs):
        order = self._get_last_order()
        if not order:
            return request.redirect(SHOP_PATH)
        filename = f"Order - {order.name}.pdf" if order.name else "Order.pdf"
        return self._render_pdf_response("sale.action_report_saleorder", order.id, filename)

    @route(["/shop/print/invoice"], type="http", auth="public", website=True, sitemap=False)
    def print_invoice(self, **_kwargs):
        order = self._get_last_order()
        if not order:
            return request.redirect(SHOP_PATH)
        invoice = order.invoice_ids and order.invoice_ids[0]
        if not invoice:
            return request.redirect(SHOP_PATH)
        filename = "%s.pdf" % (invoice.name or "Invoice")
        return self._render_pdf_response("account.account_invoices", invoice.id, filename)
