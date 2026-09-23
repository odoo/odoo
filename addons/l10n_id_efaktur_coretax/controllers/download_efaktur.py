from odoo import _, http
from odoo.http import prepare_content_disposition_header, request

# from odoo.addons.account.controllers.download_docs import _get_headers


def _get_headers(filename, filetype, content):
    return [
        ("Content-Type", filetype),
        ("Content-Length", len(content)),
        ("Content-Disposition", prepare_content_disposition_header(filename)),
        ("X-Content-Type-Options", "nosniff"),
    ]


class EfakturDownloadController(http.Controller):
    @http.route(
        '/l10n_id_efaktur_coretax/download_attachments/<models("ir.attachment"):attachments>',
        type="http",
        auth="user",
    )
    def download_invoice_attachments(self, attachments):
        attachments.check_access("read")
        assert all(
            attachment.res_id
            and attachment.res_model == "l10n_id_efaktur_coretax.document"
            for attachment in attachments
        )
        if len(attachments) == 1:
            headers = _get_headers(
                attachments.name, attachments.mimetype, attachments.raw
            )
            return request.prepare_response(attachments.raw, headers)
        else:
            filename = _("efaktur") + ".zip"
            content = attachments._prepare_zip_from_attachments()
            headers = _get_headers(filename, "zip", content)
            return request.prepare_response(content, headers)
