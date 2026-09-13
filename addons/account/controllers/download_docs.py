import io
import zipfile
from itertools import chain

from odoo import _, http
from odoo.exceptions import UserError
from odoo.http import prepare_content_disposition_header, request
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


def _get_headers(filename, filetype, content):
    return [
        ("Content-Type", filetype),
        ("Content-Length", len(content)),
        ("Content-Disposition", prepare_content_disposition_header(filename)),
        ("X-Content-Type-Options", "nosniff"),
    ]


def _prepare_zip_from_data(docs_data):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as zipfile_obj:
        for doc_data in docs_data:
            zipfile_obj.writestr(doc_data["filename"], doc_data["content"])
    return buffer.getvalue()


class AccountDocumentDownloadController(http.Controller):
    @http.route(
        '/account/download_invoice_attachments/<models("ir.attachment"):attachments>',
        type="http",
        auth="user",
    )
    def download_invoice_attachments(self, attachments):
        _debug.pipeline(
            "route",
            handler="AccountDocumentDownloadController.download_invoice_attachments",
        )
        attachments.check_access("read")
        if not all(
            attachment.res_id and attachment.res_model == "account.move"
            for attachment in attachments
        ):
            raise UserError(_("Some attachments are not linked to an invoice."))
        if len(attachments) == 1:
            headers = _get_headers(
                attachments.name, attachments.mimetype, attachments.raw
            )
            return request.prepare_response(attachments.raw, headers)
        else:
            inv_ids = attachments.mapped("res_id")
            if len(set(inv_ids)) == 1:
                invoice = request.env["account.move"].browse(inv_ids[0])
                filename = invoice._get_invoice_report_filename(extension="zip")
            else:
                filename = _("invoices") + ".zip"
            content = attachments._prepare_zip_from_attachments()
            headers = _get_headers(filename, "application/zip", content)
            return request.prepare_response(content, headers)

    @http.route(
        '/account/download_invoice_documents/<models("account.move"):invoices>/<string:filetype>',
        type="http",
        auth="user",
    )
    def download_invoice_documents_filetype(
        self, invoices, filetype, allow_fallback=True
    ):
        _debug.pipeline(
            "route",
            handler="AccountDocumentDownloadController.download_invoice_documents_filetype",
        )
        invoices.check_access("read")
        invoices.line_ids.check_access("read")
        docs_data = []
        for invoice in invoices:
            if filetype == "all" and (
                doc_data := invoice._get_invoice_legal_documents_all(
                    allow_fallback=allow_fallback
                )
            ):
                docs_data += doc_data
            elif doc_data := invoice._get_invoice_legal_documents(
                filetype, allow_fallback=allow_fallback
            ):
                if (errors := doc_data.get("errors")) and len(invoices) == 1:
                    raise UserError(
                        _("Error while creating XML:\n- %s", "\n- ".join(errors))
                    )
                docs_data.append(doc_data)
        if len(docs_data) == 1:
            doc_data = docs_data[0]
            headers = _get_headers(
                doc_data["filename"], doc_data["filetype"], doc_data["content"]
            )
            return request.prepare_response(doc_data["content"], headers)
        if len(docs_data) > 1:
            zip_content = _prepare_zip_from_data(docs_data)
            headers = _get_headers(
                _("invoices") + ".zip", "application/zip", zip_content
            )
            return request.prepare_response(zip_content, headers)
        return None

    @http.route(
        '/account/download_move_attachments/<models("account.move"):moves>',
        type="http",
        auth="user",
    )
    def download_move_attachments(self, moves):
        _debug.pipeline(
            "route",
            handler="AccountDocumentDownloadController.download_move_attachments",
        )
        moves.check_access("read")

        def rename_duplicates(docs):
            seen = {}
            for doc in docs:
                name = doc["filename"]
                if name not in seen:
                    seen[name] = 0
                else:
                    seen[name] += 1
                    base, *ext = name.rsplit(".", 1)
                    new_name = f"{base} ({seen[name]})" + (f".{ext[0]}" if ext else "")
                    doc["filename"] = new_name
                    seen[new_name] = 0
            return docs

        if docs_data := list(
            chain.from_iterable(move._get_move_zip_export_docs() for move in moves)
        ):
            docs_data = rename_duplicates(docs_data)
            zip_content = _prepare_zip_from_data(docs_data)
            headers = _get_headers(
                request.env._("Invoices") + ".zip", "application/zip", zip_content
            )
            return request.prepare_response(zip_content, headers)
        return None
