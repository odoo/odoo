# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import content_disposition, request, route
from odoo.tools import replace_exceptions, str2bool
from odoo.addons.documents.controllers.documents import ShareRoute
from werkzeug.exceptions import BadRequest


class AccountShareRoute(ShareRoute):

    @route()
    def documents_content(self, access_token, download=True):
        with replace_exceptions(ValueError, by=BadRequest):
            download = str2bool(download)
        if download:
            return super().documents_content(access_token, download)

        document = self._from_access_token(access_token, skip_log=True)
        is_public = request.env.user._is_public()
        if document.sudo(is_public).has_embedded_pdf:
            # TODO: cache the extracted pdf in the browser
            embedded_pdf = document.sudo(is_public)._extract_pdf_from_xml()
            headers = [
                ('Content-Type', 'application/pdf'),
                ('X-Content-Type-Options', 'nosniff'),
                ('Content-Length', len(embedded_pdf)),
                ('Content-Disposition', content_disposition(f"{document.name}.pdf")),
            ]
            return request.make_response(embedded_pdf, headers)

        return super().documents_content(access_token, download)
