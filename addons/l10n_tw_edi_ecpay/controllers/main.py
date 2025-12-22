# Part of Odoo. See LICENSE file for full copyright and licensing details.

import werkzeug

from odoo import http
from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.exceptions import AccessError, MissingError


class EcpayInvoiceController(http.Controller):
    @http.route("/invoice/ecpay/agreed_invoice_allowance/<int:invoice_id>", type="http", methods=['POST'], auth="public", csrf=False)
    def agreed_invoice_allowance(self, invoice_id, access_token=None, **kwargs):
        try:
            invoice = CustomerPortal._document_check_access(self, 'account.move', invoice_id, access_token)
        except (AccessError, MissingError):
            raise werkzeug.exceptions.NotFound
        if invoice:
            invoice.l10n_tw_edi_refund_state = "agreed" if kwargs["RtnCode"] == "1" else "disagreed"
        return "200"
