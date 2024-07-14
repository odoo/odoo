
from odoo import http, _
from odoo.exceptions import AccessError
from odoo.addons.documents.controllers.documents import ShareRoute

from odoo.http import request


class SpreadsheetShareRoute(ShareRoute):
    @http.route()
    def share_portal(self, share_id=None, token=None):
        share = request.env["documents.share"].sudo().browse(share_id).exists()
        if share and share.type == "ids":
            documents = share._get_documents_and_check_access(token, operation="read")
            if documents and len(documents) == 1 and documents.handler == "spreadsheet":
                return self.open_spreadsheet(share.freezed_spreadsheet_ids, token)
        return super().share_portal(share_id, token)

    @http.route(
        ["/document/spreadsheet/share/<int:share_id>/<token>/<int:document_id>"],
        type="http",
        auth="public",
        methods=["GET"],
    )
    def open_shared_spreadsheet(self, share_id, token, document_id):
        spreadsheet = (
            request.env["documents.shared.spreadsheet"]
            .sudo()
            .search([("share_id", "=", share_id), ("document_id", "=", document_id)])
        )
        return self.open_spreadsheet(spreadsheet, token)

    @http.route()
    # pylint: disable=redefined-builtin
    def download_one(self, document_id=None, access_token=None, share_id=None, **kwargs):
        document = request.env["documents.document"].sudo().browse(document_id).exists()
        if document.handler == "spreadsheet":
            share = request.env["documents.share"].sudo().browse(share_id)
            available_document = share._get_documents_and_check_access(
                access_token, operation="read"
            )
            if not available_document or document not in available_document:
                raise AccessError(_("You don't have access to this document"))
            spreadsheet = (
                request.env["documents.shared.spreadsheet"]
                .sudo()
                .search(
                    [("document_id", "=", document.id), ("share_id", "=", share_id)],
                    limit=1,
                )
            )
            stream = request.env["ir.binary"]._get_stream_from(
                spreadsheet, "excel_export", filename=document.name
            )
            return stream.get_response()
        return super().download_one(document_id, access_token, share_id, **kwargs)

    @http.route(
        ["/document/spreadsheet/data/<int:spreadsheet_id>/<token>"],
        type="http",
        auth="public",
        methods=["GET"],
    )
    def get_shared_spreadsheet_data(self, spreadsheet_id, token):
        spreadsheet = (
            request.env["documents.shared.spreadsheet"]
            .sudo()
            .browse(spreadsheet_id)
            .exists()
        )
        share = spreadsheet.share_id
        if not share:
            raise request.not_found()
        document = share._get_documents_and_check_access(token, operation="read")
        if not document:
            raise AccessError(_("You don't have access to this document"))
        stream = request.env["ir.binary"]._get_stream_from(
            spreadsheet, "spreadsheet_binary_data"
        )
        return stream.get_response()

    def open_spreadsheet(self, spreadsheet, token):
        share = spreadsheet.share_id
        if not share:
            raise request.not_found()
        documents = share._get_documents_and_check_access(token, operation="read")
        if not documents or spreadsheet.document_id not in documents:
            raise AccessError(_("You don't have access to this document"))
        if request.env.user._is_internal():
            document_id = spreadsheet.document_id.id
            return request.redirect(
                f"/web#spreadsheet_id={document_id}&action=action_open_spreadsheet&access_token={token}&share_id={share.id}"
            )
        return request.render(
            "spreadsheet.public_spreadsheet_layout",
            {
                "spreadsheet_name": spreadsheet.document_id.name,
                "share": share,
                "session_info": request.env["ir.http"].session_info(),
                "props": {
                    "dataUrl": f"/document/spreadsheet/data/{spreadsheet.id}/{token}",
                    "downloadExcelUrl": f"/document/download/{share.id}/{token}/{spreadsheet.document_id.id}",
                },
            },
        )
