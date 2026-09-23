from odoo import http
from odoo.http import request


class EcpayInvoiceController(http.Controller):
    # csrf=False: auth="receiver" admits the caller through its inbound gate
    @http.route(
        "/invoice/ecpay/agreed_invoice_allowance/<int:invoice_id>",
        type="http",
        methods=["POST"],
        auth="receiver",
        receiver="account.move:_receiver_for_ecpay_allowance",
        receiver_event="ecpay_invoice_allowance",
        csrf=False,
        typed=True,
    )
    def agreed_invoice_allowance(
        self, invoice_id: int, access_token: str | None = None, **kwargs
    ):
        if "RtnCode" not in kwargs:
            return http.Response(status=400)
        request.admission.subject.l10n_tw_edi_refund_state = (
            "agreed" if kwargs["RtnCode"] == "1" else "disagreed"
        )
        return "200"
