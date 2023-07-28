# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import io
import zipfile

from odoo import http, _
from odoo.http import request, content_disposition

class AccountEdiDocumentDownloadController(http.Controller):
    @http.route('/account/export_edi_documents', type='http', auth='user')
    def export_edi_documents(self, **args):
        ids = list(map(int, request.httprequest.args.getlist('ids')))

        moves = request.env['account.move'].browse(ids)
        moves.check_access_rights('read')
        moves.check_access_rule('read')

        attachments = moves._get_edi_doc_attachments_to_export()
        if not attachments:
            error_msg = _("No EDI documents found for export.")
            return request.not_found(error_msg)

        # Create zip file
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_DEFLATED) as zipfile_obj:
            for attachment in attachments:
                zipfile_obj.writestr(attachment.display_name, attachment.raw)
        content = buffer.getvalue()

        headers = [
            ('Content-Type', 'zip'),
            ('X-Content-Type-Options', 'nosniff'),
            ('Content-Length', len(content)),
            ('Content-Disposition', content_disposition('edi_documents.zip')),
        ]
        return request.make_response(content, headers)
