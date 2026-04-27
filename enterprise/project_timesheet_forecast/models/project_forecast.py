# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import pytz

from odoo import _, api, fields, models
from odoo.osv import expression


class Forecast(models.Model):
    _inherit = 'planning.slot'

    allow_timesheets = fields.Boolean("Allow timesheets", related='project_id.allow_timesheets', help="Timesheets can be logged on this slot.", readonly=True)
    effective_hours = fields.Float("Effective Time", compute='_compute_effective_hours', compute_sudo=True, store=True,
        help="Number of time recorded on the employee's Timesheets for this task (and its sub-tasks) during the timeframe of the shift.")
    timesheet_ids = fields.Many2many('account.analytic.line', compute='_compute_timesheet_ids', compute_sudo=True, export_string_translation=False)
    can_open_timesheets = fields.Boolean(compute='_compute_can_open_timesheet', export_string_translation=False)
    percentage_hours = fields.Float("Progress", compute='_compute_percentage_hours', compute_sudo=True, store=True)
    encode_uom_in_days = fields.Boolean(compute='_compute_encode_uom_in_days', export_string_translation=False)

    def _compute_encode_uom_in_days(self):
        self.encode_uom_in_days = self.env.company.timesheet_encode_uom_id == self.env.ref('uom.product_uom_day')

    @api.depends('allocated_hours', 'effective_hours')
    def _compute_percentage_hours(self):
        for forecast in self:
            if forecast.allocated_hours:
                forecast.percentage_hours = forecast.effective_hours / forecast.allocated_hours * 100
            else:
                forecast.percentage_hours = 0

    def _get_timesheet_domain(self):
        '''
        Returns the domain used to fetch the timesheets, None is returned in case there would be no match
        '''
        self.ensure_one()
        if not self.project_id:
            return None
        domain = [
            ('employee_id', '=', self.employee_id.id),
            ('date', '>=', self.start_datetime.date()),
            ('date', '<=', self.end_datetime.date())
        ]
        if self.project_id:
            domain = expression.AND([[('project_id', '=', self.project_id.id)], domain])
        return domain

    @api.depends('timesheet_ids')
    def _compute_effective_hours(self):
        for forecast in self:
            forecast.effective_hours = sum(
                timesheet.unit_amount
                for timesheet in forecast.timesheet_ids
            )

    @api.depends('employee_id', 'start_datetime', 'end_datetime', 'project_id.timesheet_ids.unit_amount')
    def _compute_timesheet_ids(self):
        self.timesheet_ids = False
        Timesheet = self.env['account.analytic.line']
        for forecast in self:
            if forecast.project_id and forecast.start_datetime and forecast.end_datetime:
                domain = forecast._get_timesheet_domain()
                if domain:
                    forecast.timesheet_ids = Timesheet.search(domain)

    def _read_group_fields_nullify(self):
        return super()._read_group_fields_nullify() + ['effective_hours', 'effective_hours_cost', 'percentage_hours']

    @api.depends_context('uid')
    @api.depends('user_id', 'timesheet_ids')
    def _compute_can_open_timesheet(self):
        # A timesheet approver will be able to open any slot's timesheets, however
        # a regular employee will need to be a timesheet user AND be assigned to this slot
        # to be able to open them.
        is_approver = self.env.user.has_group('hr_timesheet.group_hr_timesheet_approver')
        is_user = is_approver or self.env.user.has_group('hr_timesheet.group_hr_timesheet_user')
        if not is_user:
            self.can_open_timesheets = False
        else:
            for slot in self:
                if (is_approver or (is_user and self.env.user == slot.user_id)):
                    slot.can_open_timesheets = True
                else:
                    slot.can_open_timesheets = False

    def _gantt_progress_bar_project_id(self, res_ids, start, stop):
        planning_read_group = self.env['planning.slot']._read_group(
            [('project_id', 'in', res_ids), ('start_datetime', '<=', stop), ('end_datetime', '>=', start)],
            ['project_id'],
            ['allocated_hours:sum'],
        )
        dict_values_per_project = {
            project.id: {
                'value': allocated_hours_sum,
                'max_value': project.sudo().allocated_hours
            }
            for project, allocated_hours_sum in planning_read_group
        }
        project_dict = {
            project.id: project.allocated_hours
            for project in self.env['project.project'].sudo().search([('id', 'in', res_ids)])
        }
        for project_id, allocated_hours in project_dict.items():
            if project_id not in dict_values_per_project:
                dict_values_per_project[project_id] = {
                    'value': 0.0,
                    'max_value': allocated_hours,
                }
        return dict_values_per_project

    def _gantt_progress_bar(self, field, res_ids, start, stop):
        if field == 'project_id':
            start, stop = pytz.utc.localize(start), pytz.utc.localize(stop)
            return dict(
                self._gantt_progress_bar_project_id(res_ids, start, stop),
                warning=_("This project isn't expected to have slot during this period."),
            )
        return super()._gantt_progress_bar(field, res_ids, start, stop)

    def action_open_timesheets(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('hr_timesheet.timesheet_action_all')
        # Remove all references to the original action, to avoid studio and be able to change the action name
        action.pop('id', None)
        action.pop('xml_id', None)
        action.pop('display_name', None)
        action.update({
            'name': _('Timesheets'),
            'domain': self._get_timesheet_domain(),
            'view_mode': 'list,grid,kanban,pivot,graph,form',
            'mobile_view_mode': 'grid',
            'views': [
                [self.env.ref('hr_timesheet.timesheet_view_tree_user').id, 'list'],
                [self.env.ref('timesheet_grid.timesheet_view_grid_by_employee').id, 'grid'],
                [self.env.ref('hr_timesheet.view_kanban_account_analytic_line').id, 'kanban'],
                [self.env.ref('hr_timesheet.view_hr_timesheet_line_pivot').id, 'pivot'],
                [self.env.ref('hr_timesheet.view_hr_timesheet_line_graph_all').id, 'graph'],
                [self.env.ref('hr_timesheet.hr_timesheet_line_form').id, 'form'],
            ],
        })
        action['context'] = {
            'default_date': self.start_datetime.date()\
                if self.start_datetime < fields.Datetime.now() else fields.Date.today(),
            'default_employee_id': self.employee_id.id,
            'default_project_id': self.project_id.id,
            'grid_anchor': self.start_datetime.date(),
        }
        if self.duration < 24:
            action['context']['default_unit_amount'] = self.allocated_hours
        return action
