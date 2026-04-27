# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _
from odoo.addons.project.controllers.portal import ProjectCustomerPortal

class ProjectPortal(ProjectCustomerPortal):
    def _task_get_searchbar_sortings(self, milestones_allowed, project=False):
        return super()._task_get_searchbar_sortings(milestones_allowed, project) | {
            'planned_date_begin asc': {'label': _('Planned Date'), 'sequence': 70},
        }
