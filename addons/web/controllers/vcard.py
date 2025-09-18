import importlib.util
import io
import zipfile

from odoo import _, http
from odoo.exceptions import UserError
from odoo.http import content_disposition, request


class Partner(http.Controller):
    @http.route(
        [
            '/web_enterprise/partner/<model("res.partner"):partner>/vcard',
            "/web/partner/vcard",
        ],
        type="http",
        auth="user",
    )
    def download_vcard(self, partner_ids=None, partner=None, **kwargs):
        if importlib.util.find_spec("vobject") is None:
            raise UserError(_("vobject library is not installed"))

        partners = request.env["res.partner"]
        if partner_ids:
            partner_ids = list(
                filter(
                    None,
                    (int(pid) for pid in partner_ids.split(",") if pid.isdigit()),
                )
            )
            partners = request.env["res.partner"].browse(partner_ids)
            if len(partners) > 1:
                buffer = io.BytesIO()
                with zipfile.ZipFile(buffer, "w") as zipf:
                    for p in partners:
                        label = p.name or p.email or f"contact_{p.id}"
                        zipf.writestr(f"{label}.vcf", p._get_vcard_file())
                zip_data = buffer.getvalue()
                return request.make_response(
                    zip_data,
                    [
                        ("Content-Type", "application/zip"),
                        ("Content-Length", len(zip_data)),
                        (
                            "Content-Disposition",
                            content_disposition("Contacts.zip"),
                        ),
                    ],
                )

        if partner or partners:
            partner = partner or partners
            content = partner._get_vcard_file()
            return request.make_response(
                content,
                [
                    ("Content-Type", "text/vcard"),
                    ("Content-Length", len(content)),
                    (
                        "Content-Disposition",
                        content_disposition(
                            f"{partner.name or partner.email or f'contact_{partner.id}'}.vcf"
                        ),
                    ),
                ],
            )

        return request.not_found()
