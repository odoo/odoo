# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http, _
from odoo.http import request
from odoo.addons.account.controllers.download_docs import _get_headers


class EfakturDownloadController(http.Controller):

    @http.route('/l10n_id_efaktur/download_attachments/<models("ir.attachment"):attachments>', type='http', auth='user')
    def download_invoice_attachments(self, attachments):
        attachments.check_access('read')
        assert all(attachment.res_id and attachment.res_model == 'l10n_id_efaktur.document' for attachment in attachments)
        if len(attachments) == 1:
            headers = _get_headers(attachments.name, attachments.mimetype, attachments.raw)
            return request.make_response(attachments.raw, headers)
        else:
            filename = _('efaktur') + '.zip'
            content = attachments._build_zip_from_attachments()
            headers = _get_headers(filename, 'zip', content)
            return request.make_response(content, headers)
