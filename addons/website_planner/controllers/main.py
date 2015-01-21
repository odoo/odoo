# -*- coding: utf-8 -*-

import json

from openerp import http
from openerp.http import request


class WebsitePlanner(http.Controller):

    @http.route('/planner/website_planner', type='json', auth='user', website=True)
    def get_website_planner(self, **kw):
        planner = request.env.ref('website_planner.planner_website')
        return {
            'id': planner.id,
            'menu_id': [planner.menu_id.id],
            'view_id': [planner.view_id.id],
            'progress': planner.progress,
            'tooltip_planner': planner.tooltip_planner,
            'data': planner.data and json.loads(planner.data) or {},
            'planner_application': planner.planner_application
        }
