# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
from odoo import http
from odoo.http import request


class I18nServer(http.Controller):
    @http.route(["/i18n/<string:version>/<string:code>.tar.xz"], type="http", auth="public")
    def pack(self, version, code, **kw):
        pack = request.env["i18n.pack"].search(
            [("version", "=", version), ("lang_code", "=", code)]
        )
        if not pack:
            # FIXME this is incompatible with stream
            response = request.render(
                "i18n_server.translation_not_found", {"lang": code, "version": version}
            )
            response.status_code = 404
            return response

        filename = code + ".tar.xz"
        status, headers, content = request.env["ir.http"].binary_content(
            model="i18n.pack", id=pack.id, field="content", filename=filename, download=True
        )

        if status != 200:
            return request.env["ir.http"]._response_by_status(status, headers, content)
        content_base64 = base64.b64decode(content)
        headers.append(("Content-Length", len(content_base64)))
        return request.make_response(content_base64, headers)
