# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast
import datetime
import json

from odoo import api, fields, models, _, _lt
from odoo.osv import expression


class Project(models.Model):
    _inherit = 'project.project'

    total_forecast_time = fields.Integer(compute='_compute_total_forecast_time',
                                         help="Total number of forecast hours in the project rounded to the unit.", compute_sudo=True)

    def _compute_total_forecast_time(self):
        shifts_read_group = self.env['planning.slot']._read_group(
            [('start_datetime', '!=', False), ('end_datetime', '!=', False), ('project_id', 'in', self.ids)],
            ['project_id'],
            ['allocated_hours:sum'],
        )
        shifts_per_project = {project.id: int(round(allocated_hours_sum)) for project, allocated_hours_sum in shifts_read_group}
        for project in self:
            project.total_forecast_time = shifts_per_project.get(project.id, 0)

    def action_project_forecast_from_project(self):
        action = self.env["ir.actions.actions"]._for_xml_id("project_forecast.project_forecast_action_from_project")
        first_slot = self.env['planning.slot'].search([('start_datetime', '>=', datetime.datetime.now()), ('project_id', '=', self.id)], limit=1, order="start_datetime")
        context = {
            'default_project_id': self.id,
            'search_default_project_id': [self.id],
            **ast.literal_eval(action['context']),
            'search_default_group_by_resource': False,
        }
        if first_slot:
            context['initialDate'] = first_slot.start_datetime
        elif self.date_start and self.date_start >= datetime.date.today():
            context['initialDate'] = self.date_start
        action.update(
            context=context,
            domain=[('start_datetime', '!=', False), ('end_datetime', '!=', False)],
        )
        return action

    # ----------------------------
    #  Project Updates
    # ----------------------------

    def _get_stat_buttons(self):
        buttons = super(Project, self)._get_stat_buttons()
        buttons.append({
            'icon': 'tasks',
            'text': _lt('Planned'),
            'number': '%s Hours' % (self.total_forecast_time),
            'action_type': 'object',
            'action': 'action_project_forecast_from_project',
            'additional_context': json.dumps({
                'active_id': self.id,
            }),
            'show': True,
            'sequence': 12,
        })
        return buttons
