from werkzeug.exceptions import Forbidden

from odoo import http
from odoo.exceptions import AccessError, MissingError
from odoo.http import request

from odoo.addons.portal.controllers.portal import CustomerPortal


class EcpayInvoiceController(http.Controller):
    @http.route(
        "/invoice/ecpay/agreed_invoice_allowance/<int:invoice_id>",
        type="http",
        methods=["POST"],
        auth="public",
        csrf=False,
    )
    def agreed_invoice_allowance(self, invoice_id, access_token=None, **kwargs):
        httprequest = request.httprequest
        invoice_sudo = request.env["account.move"].sudo().browse(invoice_id).exists()
        if not invoice_sudo:
            request.env["inbound.access.log"]._record_unknown_caller(
                "account.move",
                f"ECPay allowance for invoice {invoice_id}",
                httprequest.remote_addr,
                user_agent=httprequest.headers.get("User-Agent"),
            )
            return http.Response(status=404)

        def check_access():
            try:
                CustomerPortal._document_check_access(
                    self, "account.move", invoice_id, access_token
                )
            except AccessError, MissingError:
                raise Forbidden from None

        receiver = request.env["integration.receiver"]._for_record(
            invoice_sudo.company_id,
            request.env._(
                "%(company)s ECPay allowance callbacks",
                company=invoice_sudo.company_id.name,
            ),
            purpose="ecpay_allowance",
        )
        if not receiver._admit_checked_request(
            check_access, event_type="ecpay_invoice_allowance"
        ):
            return http.Response(status=404)
        if "RtnCode" not in kwargs:
            return http.Response(status=400)
        invoice_sudo.l10n_tw_edi_refund_state = (
            "agreed" if kwargs["RtnCode"] == "1" else "disagreed"
        )
        return "200"
