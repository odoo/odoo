# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo import api, fields, models, _, _lt

class Project(models.Model):
    _inherit = 'project.project'

    display_planning_timesheet_analysis = fields.Boolean(compute='_compute_display_planning_timesheet_analysis', help='Should we display the planning and timesheet analysis button?')

    @api.depends('allow_timesheets')
    @api.depends_context('uid')
    def _compute_display_planning_timesheet_analysis(self):
        is_user_authorized = self.env.user.has_group('planning.group_planning_manager') and self.env.user.has_group('hr_timesheet.group_hr_timesheet_approver')
        if not is_user_authorized:
            self.display_planning_timesheet_analysis = False
        else:
            for project in self:
                project.display_planning_timesheet_analysis = project.allow_timesheets

    # -------------------------------------------
    # Actions
    # -------------------------------------------

    def open_timesheets_planning_report(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("project_timesheet_forecast.project_timesheet_forecast_report_action")
        action.update({
            'display_name': _("%(name)s's Timesheets and Planning Analysis", name=self.name),
            'domain': [('project_id', '=', self.id)],
            'context': {
                'pivot_row_groupby': ['entry_date:month'],
            }
        })
        return action

    # ----------------------------
    #  Project Updates
    # ----------------------------

    def _get_stat_buttons(self):
        buttons = super(Project, self)._get_stat_buttons()
        buttons.append({
            'icon': 'clock-o',
            'text': _lt('Timesheets and Planning'),
            'action_type': 'object',
            'action': 'open_timesheets_planning_report',
            'additional_context': json.dumps({
                'active_id': self.id,
            }),
            'show': self.display_planning_timesheet_analysis,
            'sequence': 63,
        })
        return buttons
