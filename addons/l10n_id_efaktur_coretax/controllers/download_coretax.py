# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request
from odoo.http.stream import content_disposition


def _get_headers(filename, filetype, content):
    return [
        ('Content-Type', filetype),
        ('Content-Length', len(content)),
        ('Content-Disposition', content_disposition(filename)),
        ('X-Content-Type-Options', 'nosniff'),
    ]


class CoretaxDownloadController(http.Controller):

    @http.route('/l10n_id_efaktur_coretax/download_attachments/<models("ir.attachment"):attachments>', type='http', auth='user')
    def download_coretax_attachments(self, attachments):
        attachments.check_access('read')
        assert all(attachment.res_id and attachment.res_model == 'l10n_id_efaktur_coretax.document' for attachment in attachments)
        if len(attachments) == 1:
            content = attachments.raw.content
            headers = _get_headers(attachments.name, attachments.mimetype, content)
            return request.make_response(content, headers)
        else:
            documents = request.env['l10n_id_efaktur_coretax.document'].browse(set(attachments.mapped('res_id')))
            document_types = set(documents.mapped('document_type'))
            # Name the archive after the kind of document it holds
            filename = '%s.zip' % (document_types.pop() if len(document_types) == 1 else 'coretax')
            content = attachments._build_zip_from_attachments()
            headers = _get_headers(filename, 'zip', content)
            return request.make_response(content, headers)
