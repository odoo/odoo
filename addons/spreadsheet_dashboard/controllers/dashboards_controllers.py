# Part of Odoo. See LICENSE file for full copyright and licensing details.

from http import HTTPStatus

import werkzeug.http

from odoo.http import Controller, request, route


class DashboardDataRoute(Controller):
    @route(
        ['/spreadsheet/dashboard/data/<model("spreadsheet.dashboard"):dashboard>'],
        type='http',
        auth='user',
        readonly=True,
    )
    def get_dashboard_data(self, dashboard):
        dashboard = dashboard.exists()
        if not dashboard:
            raise request.not_found()
        if dashboard._dashboard_is_empty() and dashboard.sample_dashboard_file_path:
            sample_data = dashboard._get_sample_dashboard()
            if sample_data:
                return request.make_json_response({
                    'snapshot': sample_data,
                    'is_sample': True,
                })
        etag = dashboard._get_dashboard_etag()
        modified = werkzeug.http.is_resource_modified(
            request.httprequest.environ,
            etag=etag,
        )
        if not modified:
            return request.make_response('', headers=[('ETag', etag), ('Cache-Control', 'no-cache, private')], status=HTTPStatus.NOT_MODIFIED)
        body = dashboard._get_serialized_readonly_dashboard()
        headers = [
            ('Content-Length', len(body)),
            ('Cache-Control', 'no-cache, private'),
            ('ETag', etag),
            ('Content-Type', 'application/json; charset=utf-8'),
        ]
        return request.make_response(body, headers)
