# -*- coding: utf-8 -*-

from openerp import http
from openerp.http import request


class PlannerController(http.Controller):

    @http.route('/planner/render', type='json', auth='user')
    def render(self, view_id, planner_app, **kw):
        return request.env['planner.planner'].render(view_id, planner_app)

    @http.route('/planner/update', type='json', auth='user')
    def update_planner(self, planner_id, data, progress=0, **kw):
        return request.env['planner.planner'].browse(planner_id).write({'data': data, 'progress':progress})
