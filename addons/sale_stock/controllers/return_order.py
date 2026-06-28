# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from markupsafe import Markup, escape
from werkzeug.exceptions import BadRequest

from odoo.exceptions import AccessError, MissingError
from odoo.http import request, route
from odoo.http.stream import content_disposition

from odoo.addons.sale.controllers import portal as sale_portal


class CustomerPortal(sale_portal.CustomerPortal):
    @route("/my/order/return_data", type="jsonrpc", auth="user", readonly=True)
    def my_order_return_data(self, order_id, access_token):
        """Prepare return details of order depending on deliveries.

        :param int order_id: The order for which we are preparing return content.
        :param str access_token: The portal access_token of the specified order.
        :return: A dict containing a list of returnable lines vals depending on deliveries.
        :rtype: dict.
        """
        try:
            order_sudo = self._document_check_access(
                "sale.order", order_id, access_token=access_token
            )
        except (AccessError, MissingError):
            return {"error": "Invalid order."}

        if not order_sudo._is_portal_return_allowed():
            return {"error": "Returns are not allowed for this order."}

        return_data = {
            "company_name": order_sudo.company_id.name,
            "currency_id": order_sudo.currency_id.id,
            "download_label_url": f"/my/orders/{order_sudo.id}/download_return_label",
            "warehouse_address": order_sudo.warehouse_id.partner_id.address,
            "returnable_lines": [],
            "return_reasons": [
                {"id": reason.id, "name": reason.name}
                for reason in self.env["return.reason"].search([])
            ],
        }
        for line in order_sudo.order_line:
            if not line._is_returnable():
                continue
            common_vals = {
                "name": line.product_id.with_context(display_default_code=False).display_name,
                "price": line.price_unit,
                "product_id": line.product_id.id,
                "product_img_url": f"/web/image/product.product/{line.product_id.id}/image_128",
            }
            for move in line.move_ids:
                if not (
                    move.state == "done" and move.picking_id.picking_type_code == "outgoing"
                ):  # Skip non-delivered or non-outgoing moves
                    continue
                move_vals = move._prepare_return_data()
                if move_vals["remaining_delivered_qty"] > 0:
                    return_data["returnable_lines"].append({**common_vals, **move_vals})

        return return_data

    @route("/my/orders/<int:order_id>/download_return_label", type="http", auth="user")
    def order_return_label(
        self, order_id, access_token=None, return_details=None, return_reason_id=None
    ):
        """Render a PDF summarizing product returns per picking.

        Each picking is rendered on a separate page, listing the returned products along with the
        selected return reason.

        :param int order_id: The order for which we are preparing return content.
        :param str access_token: The portal access_token of the specified order.
        :param str return_details: JSON-encoded mapping of move IDs to returned quantities.
        :param str return_reason_id: Selected return reason id.
        :return: HTTP response containing the PDF document.
        :rtype: werkzeug.wrappers.Response
        """
        if not return_details or not return_reason_id:
            raise BadRequest("Missing required parameters.")
        try:
            order_sudo = self._document_check_access(
                "sale.order", order_id, access_token=access_token
            )
        except (AccessError, MissingError):
            return request.redirect("/my")

        if not order_sudo._is_portal_return_allowed():
            raise BadRequest("Returns are not allowed for this order.")

        raw_qtys = json.loads(return_details)
        # Group moves and the return qtys by picking
        move_qty_by_picking = {}
        for move in order_sudo.picking_ids.move_ids.filtered(lambda m: str(m.id) in raw_qtys):
            move_qty_by_picking.setdefault(move.picking_id, {})[move] = raw_qtys[str(move.id)]

        return_reason = self.env["return.reason"].browse(int(return_reason_id))
        # Generate a return label with the returned products
        return_data = {
            "wh_address_id": order_sudo.warehouse_id.partner_id,
            "move_qty_by_picking": move_qty_by_picking,
            "return_reason": return_reason,
        }
        pdf = (
            self
            .env["ir.actions.report"]
            .sudo()
            ._render_qweb_pdf(
                "sale_stock.action_report_return_label",
                [picking.id for picking in move_qty_by_picking],
                data=return_data,
            )[0]
        )

        # Log the returned products on the order
        return_message = self._build_return_log_message(move_qty_by_picking, return_reason)
        order_sudo.message_post(body=Markup("%s") % return_message)

        label_name = f"Return-{order_sudo.name}.pdf"
        pdfhttpheaders = [
            ("Content-Type", "application/pdf"),
            ("Content-Disposition", content_disposition(label_name, "inline")),
            ("Content-Length", len(pdf)),
        ]
        return request.make_response(pdf, headers=pdfhttpheaders)

    def _build_return_log_message(self, move_qty_by_picking, return_reason):
        """Build the chatter message posted when a return label is downloaded.

        :param dict move_qty_by_picking: Mapping of pickings to their {move: qty} dict.
        :param return_reason: The reason for the return.
        :return: HTML message listing the returned products and the return reason.
        :rtype: str
        """
        message = self.env._("A return label has been downloaded for the following products:<br/>")
        for picking, qty_by_move in move_qty_by_picking.items():
            message += "<br/>%s" % (self.env._("%s:") % picking.display_name)
            for move, qty in qty_by_move.items():
                message += "<br/>- %s" % escape(
                    self.env._("%(quantity)s x %(product_name)s")
                    % {
                        "quantity": int(qty),
                        "product_name": move.product_id
                        .with_context(display_default_code=False)
                        .sudo()
                        .display_name,
                    }
                )
            message += "<br/>"
        message += "<br/>%s" % (self.env._("Return reason: %s") % return_reason.name)
        return message
