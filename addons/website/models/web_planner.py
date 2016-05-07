# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.import copy
from odoo import models

class WebsitePlanner(models.Model):
    _inherit = 'web.planner'

    def _get_planner_application(self):
        planner = super(WebsitePlanner, self)._get_planner_application()
        planner.append(['planner_website', 'Website Planner'])
        return planner
