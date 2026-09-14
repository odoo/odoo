import importlib.util
import io
import zipfile

from odoo import _, http
from odoo.exceptions import UserError
from odoo.http import prepare_content_disposition_header, request
from odoo.libs.filesystem import osutil

from ..tools import debug_log as dbg


def _get_vcard_label(partner) -> str:
    return partner.name or partner.email or f"contact_{partner.id}"


class Partner(http.Controller):
    @http.route(
        [
            '/web_enterprise/partner/<model("res.partner"):partner>/vcard',
            "/web/partner/vcard",
        ],
        type="http",
        auth="user",
        readonly=True,
    )
    def download_vcard(self, partner_ids=None, partner=None, **kwargs):
        dbg.lifecycle.debug(
            "[vcard] download: %s partner=%s partner_ids=%r",
            dbg.req(),
            partner.id if partner else None,
            partner_ids,
        )
        if importlib.util.find_spec("vobject") is None:
            dbg.logic.debug("[vcard] download: vobject missing")
            raise UserError(_("vobject library is not installed"))

        partners = request.env["res.partner"]
        if partner_ids:
            partner_ids = [
                int(pid)
                for pid in partner_ids.split(",")
                if pid.isdigit() and pid != "0"
            ]
            partners = request.env["res.partner"].browse(partner_ids)
            dbg.logic.debug(
                "[vcard] download: %s -> %s",
                "zip" if len(partners) > 1 else "single",
                dbg.rec(partners),
            )
            if len(partners) > 1:
                buffer = io.BytesIO()
                with (
                    dbg.timer(request.env, "[vcard] zip %d partners", len(partners)),
                    zipfile.ZipFile(buffer, "w") as zipf,
                ):
                    used_names = set()
                    for p in partners:
                        label = _get_vcard_label(p)
                        name = osutil.clean_filename(f"{label}.vcf")
                        candidate, i = name, 1
                        while candidate in used_names:
                            candidate = osutil.clean_filename(f"{label} ({i}).vcf")
                            i += 1
                        used_names.add(candidate)
                        zipf.writestr(candidate, p._get_vcard_file())
                zip_data = buffer.getvalue()
                dbg.pipeline.debug(
                    "[vcard] download: zip %d entries, %d bytes",
                    len(used_names),
                    len(zip_data),
                )
                return request.prepare_response(
                    zip_data,
                    [
                        ("Content-Type", "application/zip"),
                        ("Content-Length", len(zip_data)),
                        (
                            "Content-Disposition",
                            prepare_content_disposition_header("Contacts.zip"),
                        ),
                    ],
                )

        if partner or partners:
            partner = partner or partners
            with dbg.timer(request.env, "[vcard] render %s", dbg.rec(partner)):
                content = partner._get_vcard_file()
            dbg.pipeline.debug(
                "[vcard] download: single %s, %d bytes", dbg.rec(partner), len(content)
            )
            return request.prepare_response(
                content,
                [
                    ("Content-Type", "text/vcard"),
                    ("Content-Length", len(content)),
                    (
                        "Content-Disposition",
                        prepare_content_disposition_header(
                            osutil.clean_filename(f"{_get_vcard_label(partner)}.vcf")
                        ),
                    ),
                ],
            )

        dbg.logic.debug("[vcard] download: no partner resolved -> 404")
        raise request.prepare_not_found_error()
