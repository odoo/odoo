# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import http
from odoo.http import request, content_disposition


class EdiDocumentDownloadController(http.Controller):
    @http.route('/account_edi/download_edi_documents', type='http', auth='user')
    def download_edi_documents(self, **args):
        ids = list(map(int, request.httprequest.args.getlist('ids')))
        content = request.env['account.move'].browse(ids)._create_zipped()
        headers = [
            ('Content-Type', 'zip'),
            ('X-Content-Type-Options', 'nosniff'),
            ('Content-Length', len(content)),
            ('Content-Disposition', content_disposition('edi_documents.zip')),
        ]
        return request.make_response(content, headers)
