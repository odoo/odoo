# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request


class HrExpenseExtractController(http.Controller):
    @http.route('/hr_expense_extract/request_done/<string:extract_document_uuid>', type='http', auth='public', csrf=False)
    def request_done(self, extract_document_uuid):
        """ This webhook is called when the extraction server is done processing a request."""
        expense_to_update = request.env['hr.expense'].sudo().search([
            ('extract_document_uuid', '=', extract_document_uuid),
            ('extract_state', 'in', ['waiting_extraction', 'extract_not_ready']),
            ('state', '=', 'draft')])
        for expense in expense_to_update:
            expense._check_ocr_status()
        return 'OK'
