# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request


class HrRecruitmentExtractController(http.Controller):
    @http.route('/hr_recruitment_extract/request_done/<string:extract_document_uuid>', type='http', auth='public', csrf=False)
    def request_done(self, extract_document_uuid):
        """ This webhook is called when the extraction server is done processing a request."""
        candidate_to_update = request.env['hr.candidate'].sudo().search([
            ('extract_document_uuid', '=', extract_document_uuid),
            ('extract_state', 'in', ['waiting_extraction', 'extract_not_ready']),
            ('is_in_extractable_state', '=', True)])
        for candidate in candidate_to_update:
            candidate._check_ocr_status()
        return 'OK'
