# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from . import wizard
from . import report


def _helpdesk_sale_timesheet_post_init(env):
    teams = env['helpdesk.team'].search([('use_helpdesk_timesheet', '=', True), ('use_helpdesk_sale_timesheet', '=', True)])

    projects = teams.filtered(lambda team: team.project_id and not team.project_id.allow_billable).mapped('project_id')
    projects.write({'allow_billable': True, 'timesheet_product_id': projects._default_timesheet_product_id()})

    for team in teams.filtered(lambda team: not team.project_id):
        team.project_id = team._create_project(team.name, team.use_helpdesk_sale_timesheet, {'allow_timesheets': True})
        env['helpdesk.ticket'].search([('team_id', '=', team.id), ('project_id', '=', False)]).write({'project_id': team.project_id.id})
