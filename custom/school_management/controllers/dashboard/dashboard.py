# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request


class UniversityDashboardController(http.Controller):
    """Executive Dashboard JSON-RPC API Controller"""

    @http.route("/university/dashboard/data", type="jsonrpc", auth="user")
    def get_dashboard_data(self, year_id=False, semester_id=False):
        """Fetch real-time executive dashboard metrics and chart series"""
        return request.env["school.dashboard"].get_role_dashboard_data(
            year_id=year_id,
            semester_id=semester_id,
        )

    @http.route("/university/dashboard/filters", type="jsonrpc", auth="user")
    def get_filter_options(self):
        """Fetch available academic years and semesters for dashboard filtering"""
        return request.env["school.dashboard"].get_filter_options()
