from werkzeug.exceptions import NotFound

from odoo import exceptions
from odoo.http import request, route
from odoo.libs.debug_log import DebugLog
from odoo.tools import consteq

from odoo.addons.sale.controllers.portal import CustomerPortal

_debug = DebugLog(__name__)


class SaleStockPortal(CustomerPortal):
    def _check_stock_picking_access(self, picking_id, access_token=None):
        picking = request.env["stock.picking"].browse(picking_id)
        picking_sudo = picking.sudo()
        try:
            picking.check_access("read")
        except exceptions.AccessError:
            if (
                not access_token
                or not picking_sudo.sale_id
                or not consteq(picking_sudo.sale_id.access_token, access_token)
            ):
                _debug.logic(
                    "picking_access_denied",
                    picking=picking_id,
                    by="no_matching_order_token",
                )
                raise
            _debug.logic("picking_access_by_token", picking=picking_sudo)
        return picking_sudo

    def _render_picking_pdf(self, report_xmlid, picking_id, access_token=None):
        try:
            picking_sudo = self._check_stock_picking_access(
                picking_id, access_token=access_token
            )
        except exceptions.AccessError, exceptions.MissingError:
            _debug.logic("picking_pdf_denied", picking=picking_id, report=report_xmlid)
            return NotFound()

        pdf = (
            request.env["ir.actions.report"]
            .sudo()
            ._render_qweb_pdf(report_xmlid, [picking_sudo.id])[0]
        )
        _debug.pipeline(
            "picking_pdf_served",
            picking=picking_sudo,
            report=report_xmlid,
            bytes=len(pdf),
        )
        return request.prepare_response(
            pdf,
            headers=[
                ("Content-Type", "application/pdf"),
                ("Content-Length", len(pdf)),
            ],
        )

    @route(
        ["/my/picking/pdf/<int:picking_id>"], type="http", auth="public", website=True
    )
    def portal_my_picking_report(self, picking_id, access_token=None, **kw):
        return self._render_picking_pdf(
            "stock.action_report_delivery", picking_id, access_token=access_token
        )

    @route(
        ["/my/picking/return/pdf/<int:picking_id>"],
        type="http",
        auth="public",
        website=True,
    )
    def portal_my_picking_return_report(self, picking_id, access_token=None, **kw):
        return self._render_picking_pdf(
            "stock.return_label_report", picking_id, access_token=access_token
        )
