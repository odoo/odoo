# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import _, api, fields, models
from odoo.tools import format_list


class Task(models.Model):
    _inherit = 'project.task'

    leave_warning = fields.Char(compute='_compute_leave_warning', compute_sudo=True, export_string_translation=False)
    is_absent = fields.Boolean(
        'Employees on Time Off', compute='_compute_leave_warning', search='_search_is_absent',
        compute_sudo=True, readonly=True, export_string_translation=False)

    @api.depends_context('lang')
    @api.depends('planned_date_begin', 'date_deadline', 'user_ids', 'project_id', 'is_closed')
    def _compute_leave_warning(self):
        def group_by_leave(data):
            mapping_leaves = defaultdict(list)
            for item in data:
                name = item['name']
                for leave in item['leaves']:
                    leave_tuple = tuple(leave.items())
                    mapping_leaves[leave_tuple].append(name)
            res = []
            for leave_tuple, names in mapping_leaves.items():
                leave_dict = dict(leave_tuple)
                res.append({'names': names, 'leaves': leave_dict})
            return res

        # Avoid NewIds issue by browsing for self.ids.
        tasks = self.with_context(prefetch_fields=False)

        if all(self._ids):
            tasks = tasks.browse(self.ids)
            tasks.fetch(['user_ids', 'project_id', 'planned_date_begin', 'date_deadline', 'is_closed'])

        assigned_tasks = tasks.filtered(
            lambda t: t.user_ids._origin.employee_id
            and t.project_id
            and t.planned_date_begin
            and t.date_deadline
            and not t.is_closed
        )
        (self - assigned_tasks).leave_warning = False
        (self - assigned_tasks).is_absent = False

        if not assigned_tasks:
            return

        min_date = min(assigned_tasks.mapped('planned_date_begin'))
        date_from = min_date if min_date > fields.Datetime.today() else fields.Datetime.today()
        leaves = self.env['hr.leave']._get_leave_interval(
            date_from=date_from,
            date_to=max(assigned_tasks.mapped('date_deadline')),
            employee_ids=assigned_tasks.user_ids._origin.employee_id
        )

        for task in assigned_tasks:
            leaves_parameters = {"validated": [], "requested": []}
            # Gather leaves parameters for each employee
            for employee in task.user_ids._origin.employee_id:
                task_leaves = leaves.get(employee.id)
                if task_leaves:
                    employee_leaves = self.env['hr.leave']._get_leave_warning_parameters(
                        task_leaves, employee, task.planned_date_begin, task.date_deadline
                    )
                    for leave_type, leaves_for_employee in employee_leaves.items():
                        if not leaves_for_employee:
                            continue
                        leaves_parameters[leave_type].append(leaves_for_employee)
            # Group leaves
            for leave_type, leaves_for_employee in leaves_parameters.items():
                leaves_parameters[leave_type] = group_by_leave(leaves_for_employee)
            warning = ''
            for leave_type, leaves_for_employee in leaves_parameters.items():
                for leave in leaves_for_employee:
                    if leave["leaves"]:
                        if leave_type == 'validated':
                            if len(leave["names"]) == 1:
                                warning += _('%(names)s is on time off %(leaves)s. \n',
                                             names=leave["names"][0],
                                             leaves=self.env['hr.leave'].format_date_range_to_string(leave["leaves"]))
                            else:
                                warning += _('%(names)s are on time off %(leaves)s. \n',
                                             names=format_list(self.env, leave["names"]),
                                             leaves=self.env['hr.leave'].format_date_range_to_string(leave["leaves"]))
                        else:
                            warning += _('%(names)s requested time off %(leaves)s. \n',
                                         names=format_list(self.env, leave["names"]),
                                         leaves=self.env['hr.leave'].format_date_range_to_string(leave["leaves"]))
            task.leave_warning = warning or False
            task.is_absent = bool(warning)
        return warning

    @api.model
    def _search_is_absent(self, operator, value):
        if operator not in ['=', '!='] or not isinstance(value, bool):
            raise NotImplementedError(_('Operation not supported'))

        tasks = self.search([
            ('user_ids.employee_id', '!=', False),
            ('project_id', '!=', False),
            ('planned_date_begin', '!=', False),
            ('date_deadline', '!=', False),
            ('is_closed', '=', False),
        ])
        if not tasks:
            return []

        min_date = min(tasks.mapped('planned_date_begin'))
        date_from = min_date if min_date > fields.Datetime.today() else fields.Datetime.today()
        mapped_leaves = self.env['hr.leave']._get_leave_interval(
            date_from=date_from,
            date_to=max(tasks.mapped('date_deadline')),
            employee_ids=tasks.mapped('user_ids.employee_id')
        )
        task_ids = []
        for task in tasks:
            employees = tasks.mapped('user_ids.employee_id')
            for employee in employees:
                if employee.id in mapped_leaves:
                    leaves = mapped_leaves[employee.id]
                    period = self.env['hr.leave']._group_leaves(leaves, employee, task.planned_date_begin, task.date_deadline)
                    if period:
                        task_ids.append(task.id)
        if operator == '!=':
            value = not value
        return [('id', 'in' if value else 'not in', task_ids)]
