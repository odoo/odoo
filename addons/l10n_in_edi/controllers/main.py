# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
import json
from odoo.addons.l10n_in_edi import utils as l10n_in_edi_utils
import werkzeug.exceptions

class ViewEinvoiceController(http.Controller):

    @http.route(['/l10n_in_edi/vieweinvoice/<int:invoice_id>'], type='http')
    def controller_view_einvoice(self, invoice_id):
        move = http.request.env['account.move'].search([('id', '=', invoice_id)])
        json_data = move and move._get_l10n_in_edi_response_json()
        if json_data:
            response_html = l10n_in_edi_utils.verify_signed_invoice(json.dumps(json_data))
            return http.request.make_response(response_html, headers=[('Content-Type', 'text/html')])
        else:
            raise werkzeug.exceptions.Forbidden()
