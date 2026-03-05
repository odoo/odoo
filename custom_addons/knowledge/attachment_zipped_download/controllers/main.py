# Copyright 2019 César Fernández Domínguez <cesfernandez@outlook.com>
# Copyright 2022 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)
from odoo import _, http
from odoo.http import request


class AttachmentZippedDownloadController(http.Controller):
    @http.route("/web/attachment/download_zip", type="http", auth="user")
    def download_zip(self, ids=None, debug=0):
        ids = [] if not ids else ids
        if len(ids) == 0:
            return
        list_ids = map(int, ids.split(","))
        out_file = request.env["ir.attachment"].browse(list_ids)._create_temp_zip()
        stream = http.Stream(
            type="data",
            data=out_file.getvalue(),
            mimetype="application/zip",
            as_attachment=True,
            download_name=_("attachments.zip"),
        )
        return stream.get_response()
