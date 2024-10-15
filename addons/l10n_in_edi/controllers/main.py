# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json

from odoo import http
from odoo.addons.l10n_in_edi import utils as l10n_in_edi_utils
from odoo.exceptions import UserError
from odoo.addons.l10n_in_edi.demo.demo_response import EINVOICE_SIGNED_RESPONSE


class ViewEinvoiceController(http.Controller):

    def _get_error_alert_message(self,message):
        return """
                <script>
                    alert("{error_message}");
                </script>
            """.format(error_message=message)

    @http.route(['/l10n_in_edi/vieweinvoice/<int:invoice_id>'], type='http', auth='public')
    def controller_view_einvoice(self, invoice_id, **kwargs):
        move = http.request.env['account.move'].browse(invoice_id)
        if move and move._get_l10n_in_edi_response_json() and move.company_id.l10n_in_edi_production_env:
            json_data = move._get_l10n_in_edi_response_json()
        else:
            json_data = EINVOICE_SIGNED_RESPONSE

        try:
            # Call the verify_signed_invoice method from the util file
            response_html = l10n_in_edi_utils.verify_signed_invoice(json.dumps(json_data))
            if '<input type="hidden" class="hdnJson" id="hdnJson" name="hdnJson" value="" />' in response_html:
                error_message = "E-invoice verification failed. It maybe because server is down or it's created for demo purpose"
                return http.request.make_response(self._get_error_alert_message(error_message), headers=[('Content-Type', 'text/html')])
            return http.request.make_response(response_html, headers=[('Content-Type', 'text/html')])
        except UserError as e:
            # Handle UserError raised by the util method
            error_message = e.args[0] or str(e)
            return http.request.make_response(self._get_error_alert_message(error_message), headers=[('Content-Type', 'text/html')])
        except Exception as e:
            # Handle other exceptions
            error_message = "An error occurred while verifying the signed invoice: {}".format(str(e))
            return http.request.make_response(self._get_error_alert_message(error_message), headers=[('Content-Type', 'text/html')])
