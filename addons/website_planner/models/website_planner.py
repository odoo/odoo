# -*- coding: utf-8 -*-

import json

from openerp import api, models


class WebsitePlanner(models.Model):
    _inherit = 'planner.planner'

    @api.model
    def _get_planner_application(self):
        planner = super(WebsitePlanner, self)._get_planner_application()
        planner.append(['planner_website', 'Website Planner'])
        return planner

    @api.model
    def _prepare_planner_website_data(self):
        return {
            'prepare_backend_url': self.prepare_backend_url,
        }

    @api.model
    def get_website_planner(self):
        planner = self.env.ref('website_planner.planner_website')
        return {
            'id': planner.id,
            'menu_id': [planner.menu_id.id],
            'view_id': [planner.view_id.id],
            'progress': planner.progress,
            'tooltip_planner': planner.tooltip_planner,
            'data': planner.data and json.loads(planner.data) or {},
            'planner_application': planner.planner_application
        }
