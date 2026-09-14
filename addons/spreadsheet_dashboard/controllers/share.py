from odoo import http
from odoo.http import request
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class DashboardShareRoute(http.Controller):
    @http.route(["/dashboard/share/<int:share_id>/<token>"], type="http", auth="public")
    def share_portal(self, share_id=None, token=None):
        share = (
            request.env["spreadsheet.dashboard.share"].sudo().browse(share_id).exists()
        )
        if not share:
            _debug.logic("dashboard_share_not_found", route="portal", share_id=share_id)
            raise request.prepare_not_found_error()
        share._check_dashboard_access(token)
        _debug.lifecycle("dashboard_share_portal_rendered", share=share)
        return request.render(
            "spreadsheet.public_spreadsheet_layout",
            {
                "spreadsheet_name": share.dashboard_id.name,
                "share": share,
                "is_frozen": True,
                "session_info": request.env["ir.http"].session_info(),
                "props": {
                    "dataUrl": f"/dashboard/data/{share.id}/{token}",
                    "downloadExcelUrl": f"/dashboard/download/{share.id}/{token}",
                    "mode": "dashboard",
                },
            },
        )

    @http.route(
        ["/dashboard/download/<int:share_id>/<token>"],
        type="http",
        auth="public",
        readonly=True,
    )
    def download(self, token=None, share_id=None):
        share = (
            request.env["spreadsheet.dashboard.share"].sudo().browse(share_id).exists()
        )
        if not share:
            _debug.logic(
                "dashboard_share_not_found", route="download", share_id=share_id
            )
            raise request.prepare_not_found_error()
        share._check_dashboard_access(token)
        _debug.lifecycle("dashboard_share_downloaded", share=share)
        stream = request.env["ir.binary"]._get_stream_from_record(
            share, "excel_export", filename=share.name
        )
        return stream.prepare_response()

    @http.route(
        ["/dashboard/data/<int:share_id>/<token>"],
        type="http",
        auth="public",
        methods=["GET"],
        readonly=True,
    )
    def get_shared_dashboard_data(self, share_id, token):
        share = (
            request.env["spreadsheet.dashboard.share"].sudo().browse(share_id).exists()
        )
        if not share:
            _debug.logic("dashboard_share_not_found", route="data", share_id=share_id)
            raise request.prepare_not_found_error()

        share._check_dashboard_access(token)
        _debug.lifecycle("dashboard_share_data_served", share=share)
        stream = request.env["ir.binary"]._get_stream_from_record(
            share, "spreadsheet_binary_data"
        )
        return stream.prepare_response()
