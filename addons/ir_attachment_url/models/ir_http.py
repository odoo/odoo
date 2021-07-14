# Copyright 2016-2018 Ildar Nasyrov <https://it-projects.info/team/iledarn>
# Copyright 2017 Dinar Gabbasov <https://it-projects.info/team/GabbasovDinar>
# Copyright 2016-2018,2021 Ivan Yelizariev <https://it-projects.info/team/yelizariev>
# Copyright 2020 Eugene Molotov <https://it-projects.info/team/em230418>
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).
import re

import werkzeug

from odoo import models


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    @classmethod
    def _find_field_attachment(cls, env, field, obj):
        while True:
            related = env[obj._name]._fields[field].related
            if related and len(related) >= 2:
                obj = obj[related[0]]
                field = related[1]
            else:
                break

        model = obj._name
        is_attachment = env[model]._fields[field].attachment
        if not is_attachment:
            return env["ir.attachment"]

        domain = [
            ("res_model", "=", model),
            ("res_field", "=", field),
            ("res_id", "=", obj.id),
            ("type", "=", "binary"),
            ("url", "!=", False),
        ]
        return (
            env["ir.attachment"]
            .sudo()
            .search_read(domain=domain, fields=["url", "mimetype", "checksum"], limit=1)
        )

    def _binary_record_content(self, record, **kw):
        field = kw.get("field", "datas")

        filename = kw.get("filename")
        mimetype = "mimetype" in record and record.mimetype or False
        content = None
        filehash = "checksum" in record and record["checksum"] or False

        field_def = record._fields[field]
        if field_def.type == "binary":
            field_attachment = self._find_field_attachment(self.env, field, record)
            if field_attachment:
                mimetype = field_attachment[0]["mimetype"]
                content = field_attachment[0]["url"]
                filehash = field_attachment[0]["checksum"]
                return 302, content, filename, mimetype, filehash

        return super(IrHttp, self)._binary_record_content(record, **kw)

    @classmethod
    def _binary_ir_attachment_redirect_content(
        cls, record, default_mimetype="application/octet-stream"
    ):
        if (
            record.type == "binary"
            and record.url
            and not re.match(r"^/(\w+)/(.+)$", record.url)
        ):
            mimetype = record.mimetype
            content = record.url
            filehash = record.checksum
            filename = record.name
            return 302, content, filename, mimetype, filehash
        return super(IrHttp, cls)._binary_ir_attachment_redirect_content(
            record, default_mimetype=default_mimetype
        )

    def _response_by_status(self, status, headers, content):
        if status == 302:
            return werkzeug.utils.redirect(content, code=302)
        return super(IrHttp, self)._response_by_status(status, headers, content)
