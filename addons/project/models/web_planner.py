# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class PlannerProject(models.Model):

    _inherit = 'web.planner'

    def _get_planner_application(self):
        planner = super(PlannerProject, self)._get_planner_application()
        planner.append(['planner_project', 'Project Planner'])
        return planner

    def _prepare_planner_project_data(self):
        return {
            'timesheet_menu': self.env.ref('hr_timesheet.timesheet_menu_root', raise_if_not_found=False),
        }
