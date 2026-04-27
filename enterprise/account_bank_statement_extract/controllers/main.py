from odoo import http
from odoo.http import request


class AccountBankStatementExtractController(http.Controller):
    @http.route('/account_bank_statement_extract/request_done/<string:extract_document_uuid>', type='http', auth='public', csrf=False)
    def request_done(self, extract_document_uuid):
        """ This webhook is called when the extraction server is done processing a request."""
        statements_to_update = request.env['account.bank.statement'].sudo().search([
            ('extract_document_uuid', '=', extract_document_uuid),
            ('extract_state', 'in', ['waiting_extraction', 'extract_not_ready']),
            ('is_in_extractable_state', '=', True)])
        for statement in statements_to_update:
            statement._check_ocr_status()
        return 'OK'
