# -*- coding: utf-8 -*-
from openerp import http

class Database(http.Controller):
    @http.route('/project_timesheet/project_timesheet_ui', type='http', auth="user")
    def project_timesheet_ui(self, **kw):
    	return http.request.render("project_timesheet.index")