from odoo import http
from odoo.http import request
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class DashboardDataRoute(http.Controller):
    @http.route(
        ['/spreadsheet/dashboard/data/<model("spreadsheet.dashboard"):dashboard>'],
        type="http",
        auth="user",
        readonly=True,
    )
    def get_dashboard_data(self, dashboard):
        dashboard = dashboard.exists()
        if not dashboard:
            _debug.logic("dashboard_data_not_found")
            raise request.prepare_not_found_error()
        cids_str = request.cookies.get("cids", str(request.env.user.company_id.id))
        cids = [int(cid) for cid in cids_str.split("-") if cid.isdigit()]
        if not cids:
            cids = [request.env.user.company_id.id]
        dashboard = dashboard.with_context(allowed_company_ids=cids)
        if dashboard._dashboard_is_empty() and dashboard.sample_dashboard_file_path:
            sample_data = dashboard._get_sample_dashboard()
            _debug.logic(
                "dashboard_sample_considered",
                dashboard=dashboard,
                served=bool(sample_data),
            )
            if sample_data:
                return request.prepare_json_response(
                    {
                        "snapshot": sample_data,
                        "is_sample": True,
                    }
                )
        with _debug.perf(
            "dashboard_data_serialized",
            cr=request.env.cr,
            dashboard=dashboard,
            companies=len(cids),
        ) as span:
            body = dashboard._get_serialized_readonly_dashboard()
            span.set(body_chars=len(body))
        headers = [
            ("Content-Length", len(body)),
            ("Content-Type", "application/json; charset=utf-8"),
        ]
        return request.prepare_response(body, headers)
