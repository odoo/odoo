# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request


class DashboardDataRoute(http.Controller):
    @http.route(
        ['/spreadsheet/dashboard/data/<model("spreadsheet.dashboard"):dashboard>'],
        type='http',
        auth='user',
        readonly=True
    )
    def get_dashboard_data(self, dashboard):
        dashboard = dashboard.exists()
        if not dashboard:
            raise request.not_found()
        cids_str = request.cookies.get('cids', str(request.env.user.company_id.id))
        cids = [int(cid) for cid in cids_str.split('-')]
        dashboard = dashboard.with_context(allowed_company_ids=cids)
        if dashboard._dashboard_is_empty() and dashboard.sample_dashboard_file_path:
            sample_data = dashboard._get_sample_dashboard()
            if sample_data:
                return request.make_json_response({
                    'snapshot': sample_data,
                    'is_sample': True,
                })
        body = dashboard._get_serialized_readonly_dashboard()
        headers = [
            ('Content-Length', len(body)),
            ('Content-Type', 'application/json; charset=utf-8'),
        ]
        return request.make_response(body, headers)
