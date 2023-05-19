# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json
import werkzeug.exceptions

from odoo import http
from odoo.addons.l10n_in_edi import utils as l10n_in_edi_utils
from odoo.tools.misc import file_open


class ViewEinvoiceController(http.Controller):

    @http.route(['/l10n_in_edi/vieweinvoice/<int:invoice_id>'], type='http', auth='public')
    def controller_view_einvoice(self, invoice_id, **kwargs):
        move = http.request.env['account.move'].search([('id', '=', invoice_id)])
        json_data = move and move._get_l10n_in_edi_response_json()
        if json_data:
            response_html = l10n_in_edi_utils.verify_signed_invoice(json.dumps(json_data))
            if '<input type="hidden" class="hdnJson" id="hdnJson" name="hdnJson" value="" />' in response_html:
                return file_open('l10n_in_edi/views/warnings.html', 'rb').read()
            return http.request.make_response(response_html, headers=[('Content-Type', 'text/html')])
        else:
            raise werkzeug.exceptions.Forbidden()
