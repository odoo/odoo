# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import wizard
from . import report


def _helpdesk_timesheet_post_init(env):
    teams = env['helpdesk.team'].search([('use_helpdesk_timesheet', '=', True), ('project_id', '=', False), ('use_helpdesk_sale_timesheet', '=', False)])

    for team in teams:
        team.project_id = team._create_project(team.name, team.use_helpdesk_sale_timesheet, {'allow_timesheets': True})
        env['helpdesk.ticket'].search([('team_id', '=', team.id), ('project_id', '=', False)]).write({'project_id': team.project_id.id})

def _helpdesk_timesheet_uninstall(env):

    def update_action_window(xmlid):
        act_window = env.ref(xmlid, raise_if_not_found=False)
        if act_window and act_window.domain and 'helpdesk_team' in act_window.domain:
            act_window.domain = [('is_internal_project', '=', False)]

    update_action_window('project.open_view_project_all')
    update_action_window('project.open_view_project_all_group_stage')
