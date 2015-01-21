# -*- coding: utf-8 -*-

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
