# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http, _
from odoo.http import request, content_disposition


def _get_zip_headers(content, filename):
    return [
        ('Content-Type', 'zip'),
        ('X-Content-Type-Options', 'nosniff'),
        ('Content-Length', len(content)),
        ('Content-Disposition', content_disposition(filename)),
    ]


class AccountDocumentDownloadController(http.Controller):
    @http.route('/account/export_zip_documents', type='http', auth='user')
    def export_zip_documents(self, **args):
        """ Download zipped attachments. """
        ids = list(map(int, request.httprequest.args.getlist('ids')))
        filename = request.httprequest.args.get('filename')
        attachments = request.env['ir.attachment'].browse(ids)
        attachments.check_access_rights('read')
        attachments.check_access_rule('read')
        content = attachments._build_zip_from_attachments()
        headers = _get_zip_headers(content, filename)
        return request.make_response(content, headers)
