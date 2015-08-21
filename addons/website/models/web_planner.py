# -*- coding: utf-8 -*-
from odoo import api, models


class WebsitePlanner(models.Model):
    _inherit = 'web.planner'

    @api.model
    def _get_planner_application(self):
        planner = super(WebsitePlanner, self)._get_planner_application()
        planner.append(['planner_website', 'Website Planner'])
        return planner
