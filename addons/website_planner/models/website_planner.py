# -*- coding: utf-8 -*-

import json

from openerp import api, models


class WebsitePlanner(models.Model):
    _inherit = 'planner.planner'

    @api.model
    def _get_planner_application(self):
        Planner = super(WebsitePlanner, self)._get_planner_application()
        Planner.append(['planner_website', 'Website Planner'])
        return Planner

    @api.model
    def _prepare_planner_website_data(self):
        return {
            'prepare_backend_url': self.prepare_backend_url,
        }

    @api.model
    def get_website_planner(self):
        Planner = self.env.ref('website_planner.planner_website')
        return {
            'id': Planner.id,
            'menu_id': [Planner.menu_id.id],
            'view_id': [Planner.view_id.id],
            'progress': Planner.progress,
            'tooltip_planner': Planner.tooltip_planner,
            'data': Planner.data and json.loads(Planner.data) or {},
            'planner_application': Planner.planner_application
        }
