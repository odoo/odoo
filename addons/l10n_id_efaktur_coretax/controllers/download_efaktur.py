# Part of Odoo. See LICENSE file for full copyright and licensing details.

import io
import zipfile

from odoo import http, _
from odoo.http import request, content_disposition
# from odoo.addons.account.controllers.download_docs import _get_headers

def _get_headers(filename, filetype, content):
    return [
        ('Content-Type', filetype),
        ('Content-Length', len(content)),
        ('Content-Disposition', content_disposition(filename)),
        ('X-Content-Type-Options', 'nosniff'),
    ]

class EfakturDownloadController(http.Controller):

    @http.route('/l10n_id_efaktur_coretax/download_attachments/<models("ir.attachment"):attachments>', type='http', auth='user')
    def download_invoice_attachments(self, attachments):
        attachments.check_access_rights('read')
        assert all(attachment.res_id and attachment.res_model == 'l10n_id_efaktur_coretax.document' for attachment in attachments)
        if len(attachments) == 1:
            headers = _get_headers(attachments.name, attachments.mimetype, attachments.raw)
            return request.make_response(attachments.raw, headers)
        else:
            filename = _('efaktur') + '.zip'
            # to replace _build_zip_from_attachments
            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_DEFLATED) as zipfile_obj:
                for attachment in attachments:
                    zipfile_obj.writestr(attachment.display_name, attachment.raw)
            content = buffer.getvalue()
            headers = _get_headers(filename, 'zip', content)
            return request.make_response(content, headers)
