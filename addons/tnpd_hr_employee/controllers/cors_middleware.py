# Part of TNPD Prison HR Employee Extension.
# License: LGPL-3
#
# CORS preflight handler for the Employee Self-Service Portal.
# Required for cross-origin (production) deployments where the frontend
# and Odoo backend are on different origins.
#
# NOTE: Access-Control-Allow-Credentials is set to 'true' so the browser
# accepts the Odoo session_id cookie in cross-origin requests.
# Access-Control-Allow-Origin must therefore be an explicit origin (never '*').

from odoo import http
from odoo.http import request


class EmployeePortalCORS(http.Controller):

    @http.route(
        [
            '/api/employee-portal/auth',
            '/api/employee-portal/whoami',
            '/api/employee-portal/logout',
            '/api/employee-portal/profile',
            '/api/employee-portal/transfers',
            '/api/employee-portal/notifications',
            '/api/employee-portal/notifications/mark-read',
            '/api/employee-portal/change-password',
        ],
        auth='none',
        type='http',
        methods=['OPTIONS'],
        csrf=False,
    )
    def employee_portal_preflight(self, **_kw):
        """
        Handle CORS preflight (OPTIONS) requests.

        Browsers send an OPTIONS request before any cross-origin POST/PUT or
        any request with a custom header. Without this handler, all employee
        portal API calls are blocked by CORS policy in production.

        With credentials=true, the browser accepts the session_id cookie
        but requires a specific (non-wildcard) origin in the response.
        """
        origin = request.httprequest.headers.get('Origin', '*')
        headers = [
            ('Access-Control-Allow-Origin',      origin),
            ('Access-Control-Allow-Credentials', 'true'),
            ('Access-Control-Allow-Methods',     'GET, POST, PUT, OPTIONS'),
            ('Access-Control-Allow-Headers',     'Content-Type, Authorization'),
            ('Access-Control-Max-Age',           '86400'),
            ('Content-Length',                   '0'),
        ]
        return request.make_response('', headers=headers, status=204)
