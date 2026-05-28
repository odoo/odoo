# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import AccessError, MissingError
from odoo.http import request, route

from odoo.addons.sale.controllers.portal import CustomerPortal


class SaleStockPortal(CustomerPortal):
    @route(
        ["/my/orders/<int:order_id>/picking/<int:picking_id>"],
        type="http",
        auth="public",
        website=True,
    )
    def portal_my_picking_report(self, order_id, picking_id, access_token=None, **kw):
        """Print delivery slip."""
        try:
            order_sudo = self._document_check_access(
                "sale.order", order_id, access_token=access_token
            )
        except (AccessError, MissingError):
            return request.redirect("/my")

        picking_sudo = request.env["stock.picking"].browse([picking_id]).sudo().exists()
        if picking_sudo.sale_id.id != order_sudo.id:
            return request.redirect(order_sudo.access_url)

        # print report with sudo, since it require access to product, taxes, payment term etc.. and portal does not have those access rights.
        pdf = (
            request
            .env["ir.actions.report"]
            .sudo()
            ._render_qweb_pdf("stock.action_report_delivery", [picking_sudo.id])[0]
        )
        pdfhttpheaders = [("Content-Type", "application/pdf"), ("Content-Length", len(pdf))]
        return request.make_response(pdf, headers=pdfhttpheaders)

    @route(
        ["/my/orders/<int:order_id>/picking/<int:picking_id>/return/pdf"],
        type="http",
        auth="public",
        website=True,
    )
    def portal_my_picking_return_report(self, order_id, picking_id, access_token=None, **kw):
        """Print return label for customer, using either access rights or access token
        to be sure customer has access"""
        try:
            order_sudo = self._document_check_access(
                "sale.order", order_id, access_token=access_token
            )
        except (AccessError, MissingError):
            return request.redirect("/my")

        picking_sudo = request.env["stock.picking"].browse([picking_id]).sudo().exists()
        if picking_sudo.sale_id.id != order_sudo.id:
            return request.redirect(order_sudo.access_url)

        pdf = (
            request
            .env["ir.actions.report"]
            .sudo()
            ._render_qweb_pdf("stock.return_label_report", [picking_sudo.id])[0]
        )
        pdfhttpheaders = [("Content-Type", "application/pdf"), ("Content-Length", len(pdf))]
        return request.make_response(pdf, headers=pdfhttpheaders)
