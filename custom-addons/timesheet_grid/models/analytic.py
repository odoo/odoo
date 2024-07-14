# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import ast
import re

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from dateutil.rrule import SU
from collections import defaultdict

from odoo import tools, models, fields, api, _
from odoo.addons.resource.models.utils import make_aware
from odoo.addons.resource.models.utils import filter_domain_leaf
from odoo.exceptions import UserError, AccessError
from odoo.osv import expression


class AnalyticLine(models.Model):
    _name = 'account.analytic.line'
    _inherit = ['account.analytic.line', 'timer.mixin']
    # As this model has his own data merge, avoid to enable the generic data_merge on that model.
    _disable_data_merge = True

    employee_id = fields.Many2one(group_expand="_group_expand_employee_ids")

    # reset amount on copy
    amount = fields.Monetary(copy=False)
    validated = fields.Boolean("Validated line", group_operator="bool_and", store=True, copy=False, readonly=True)
    validated_status = fields.Selection([('draft', 'Draft'), ('validated', 'Validated')], required=True,
        compute='_compute_validated_status')
    user_can_validate = fields.Boolean(compute='_compute_can_validate',
        help="Whether or not the current user can validate/reset to draft the record.")
    is_timesheet = fields.Boolean(
        string="Timesheet Line", compute_sudo=True,
        compute='_compute_is_timesheet', search='_search_is_timesheet',
        help="Set if this analytic line represents a line of timesheet.")

    duration_unit_amount = fields.Float(related="unit_amount", readonly=True, string="Timesheet Init Amount")
    unit_amount_validate = fields.Float(related="unit_amount", readonly=True, string="Timesheet Unit Time")

    display_timer = fields.Boolean(
        compute='_compute_display_timer',
        help="Technical field used to display the timer if the encoding unit is 'Hours'.")

    def _is_readonly(self):
        return super()._is_readonly() or self.validated

    def _should_not_display_timer(self):
        self.ensure_one()
        return (self.employee_id not in self.env.user.employee_ids) or self.validated

    def _compute_display_timer(self):
        uom_hour = self.env.ref('uom.product_uom_hour')
        is_uom_hour = self.env.company.timesheet_encode_uom_id == uom_hour
        for analytic_line in self:
            analytic_line.display_timer = is_uom_hour and analytic_line.encoding_uom_id == uom_hour \
                                          and not analytic_line._should_not_display_timer()

    @api.model
    def grid_unavailability(self, start_date, end_date, groupby='', res_ids=None):
        start_datetime = fields.Datetime.from_string(start_date)
        end_datetime = fields.Datetime.from_string(end_date) + relativedelta(hour=23, minute=59, second=59)
        unavailability_intervals_per_employee_id = {}
        # naive datetimes are made explicit in UTC
        from_datetime, dummy = make_aware(start_datetime)
        to_datetime, dummy = make_aware(end_datetime)
        # We need to display in grey the unavailable full days
        # We start by getting the availability intervals to avoid false positive with range outside the office hours

        def get_unavailable_dates(intervals):
            # get the dates where some work can be done in the interval. It returns a list of sets.
            available_dates = [{start.date(), end.date()} for start, end, dummy in intervals]
            # flatten the list of sets to get a simple list of dates and add it to the pile.
            availability_date_list = [date for dates in available_dates for date in dates]
            unavailable_days = []
            cur_day = from_datetime
            while cur_day <= to_datetime:
                if cur_day.date() not in availability_date_list:
                    unavailable_days.append(cur_day.date())
                cur_day = cur_day + timedelta(days=1)
            return list(set(unavailable_days))

        def get_company_unavailable_dates():
            return get_unavailable_dates(self.env.company.resource_calendar_id._work_intervals_batch(from_datetime, to_datetime)[False])

        if groupby == 'employee_id':
            employees = self.env['hr.employee'].browse(set(res_ids))
            availability_intervals_per_resource_id, calendar_work_intervals = employees.resource_id._get_valid_work_intervals(from_datetime, to_datetime)
            employee_id_per_resource_id = {emp.resource_id.id: emp.id for emp in employees}
            if not calendar_work_intervals:
                unavailability_intervals_per_employee_id[False] = get_company_unavailable_dates()
                return unavailability_intervals_per_employee_id
            if self.env.company.resource_calendar_id.id in calendar_work_intervals:
                company_unavailable_days = get_unavailable_dates(calendar_work_intervals[self.env.company.resource_calendar_id.id])
            else:
                company_unavailable_days = get_company_unavailable_dates()
            unavailability_intervals_per_employee_id = {
                employee_id:
                    get_unavailable_dates(availability_intervals_per_resource_id[resource_id])
                    if resource_id in availability_intervals_per_resource_id
                    else company_unavailable_days
                for resource_id, employee_id in employee_id_per_resource_id.items()
            }
            unavailability_intervals_per_employee_id[False] = company_unavailable_days
        else:
            unavailability_intervals_per_employee_id[False] = get_company_unavailable_dates()
        return unavailability_intervals_per_employee_id

    @api.depends('project_id')
    def _compute_is_timesheet(self):
        for line in self:
            line.is_timesheet = bool(line.project_id)

    def _search_is_timesheet(self, operator, value):
        if (operator, value) in [('=', True), ('!=', False)]:
            return [('project_id', '!=', False)]
        return [('project_id', '=', False)]

    @api.depends('validated')
    def _compute_validated_status(self):
        for line in self:
            if line.validated:
                line.validated_status = 'validated'
            else:
                line.validated_status = 'draft'

    @api.depends_context('uid')
    def _compute_can_validate(self):
        is_manager = self.user_has_groups('hr_timesheet.group_timesheet_manager')
        is_approver = self.user_has_groups('hr_timesheet.group_hr_timesheet_approver')
        for line in self:
            if is_manager or (is_approver and (
                line.employee_id.timesheet_manager_id.id == self.env.user.id or
                line.employee_id.parent_id.user_id.id == self.env.user.id or
                line.project_id.user_id.id == self.env.user.id or
                line.user_id.id == self.env.user.id)):
                line.user_can_validate = True
            else:
                line.user_can_validate = False

    def _update_last_validated_timesheet_date(self):
        max_date_per_employee = {
            employee: employee.sudo().last_validated_timesheet_date
            for employee in self.employee_id
        }
        for timesheet in self:
            max_date = max_date_per_employee[timesheet.employee_id]
            if not max_date or max_date < timesheet.date:
                max_date_per_employee[timesheet.employee_id] = timesheet.date

        employee_ids_per_date = defaultdict(list)
        for employee, max_date in max_date_per_employee.items():
            if not employee.last_validated_timesheet_date or (max_date and employee.last_validated_timesheet_date < max_date):
                employee_ids_per_date[max_date].append(employee.id)

        for date, employee_ids in employee_ids_per_date.items():
            self.env['hr.employee'].sudo().browse(employee_ids).write({'last_validated_timesheet_date': date})

    @api.model
    def _search_last_validated_timesheet_date(self, employee_ids):
        EmployeeSudo = self.env['hr.employee'].sudo()
        timesheet_read_group = self.env['account.analytic.line']._read_group(
            [
                ('validated', '=', True),
                ('project_id', '!=', False),
                ('employee_id', 'in', employee_ids),
            ],
            ['employee_id'],
            ['date:max'],
        )

        EmployeeSudo.browse(employee_ids).last_validated_timesheet_date = False
        for employee, date_max in timesheet_read_group:
            employee.sudo().last_validated_timesheet_date = date_max

    def action_validate_timesheet(self):
        notification = {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': None,
                'type': None,  #types: success,warning,danger,info
                'sticky': False,  #True/False will display for few seconds if false
            },
        }
        if not self.user_has_groups('hr_timesheet.group_hr_timesheet_approver'):
            notification['params'].update({
                'message': _("You can only validate the timesheets of employees of whom you are the manager or the timesheet approver."),
                'type': 'danger'
            })
            return notification

        analytic_lines = self.filtered_domain(self._get_domain_for_validation_timesheets())
        if not analytic_lines:
            notification['params'].update({
                'message': _("You cannot validate the selected timesheets as they either belong to employees who are not part of your team or are not in a state that can be validated. This may be due to the fact that they are dated in the future."),
                'type': 'danger',
            })
            return notification

        analytic_lines._stop_all_users_timer()

        analytic_lines.sudo().write({'validated': True})
        analytic_lines._update_last_validated_timesheet_date()
        # Interrupt the timesheet with a timer running that is before the last validated date for each employee
        running_analytic_lines = self.env['account.analytic.line'].search([
            ('employee_id', 'in', analytic_lines.employee_id.ids),
            ('date', '<', max(analytic_lines.employee_id.sudo().mapped('last_validated_timesheet_date'))),
            ('is_timer_running', '=', True),
        ])
        running_analytic_lines.filtered(
            lambda aal: aal.date < aal.employee_id.last_validated_timesheet_date)._stop_all_users_timer()
        if self.env.context.get('use_notification', True):
            notification['params'].update({
                'message': _("The timesheets have successfully been validated."),
                'type': 'success',
                'next': {'type': 'ir.actions.act_window_close'},
            })
            return notification
        return True

    def action_invalidate_timesheet(self):
        notification = {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': None,
                'type': None,
                'sticky': False,
            },
        }
        if not self.user_has_groups('hr_timesheet.group_hr_timesheet_approver'):
            raise AccessError(_("You can only reset to draft the timesheets of employees of whom you are the manager or the timesheet approver."))
        #Use the same domain for validation but change validated = False to validated = True
        domain = self._get_domain_for_validation_timesheets(validated=True)
        analytic_lines = self.filtered_domain(domain)
        if not analytic_lines:
            notification['params'].update({
                'message': _('There are no timesheets to reset to draft or they have already been invoiced.'),
                'type': 'warning',
            })
            return notification

        analytic_lines.sudo().write({'validated': False})
        self.env['account.analytic.line']._search_last_validated_timesheet_date(analytic_lines.employee_id.ids)
        if self.env.context.get('use_notification', True):
            notification['params'].update({
                'message': _("The timesheets have successfully been reset to draft."),
                'type': 'success',
                'next': {'type': 'ir.actions.act_window_close'},
            })
            return notification
        return True

    def check_if_allowed(self, vals=None, delete=False,):
        if not self.user_has_groups('hr_timesheet.group_timesheet_manager'):
            is_timesheet_approver = self.user_has_groups('hr_timesheet.group_hr_timesheet_approver')
            employees = self.env['hr.employee'].with_context(active_test=False).search([
                ('id', 'in', self.employee_id.ids),
                ('user_id', '!=', self._uid),
                '|', ('parent_id.user_id', '=', self._uid),
                '|', ('timesheet_manager_id', '=', self._uid),
                '|', ('id', 'in', self.env.user.employee_id.subordinate_ids.ids),
                '&', ('parent_id', '=', False), ('timesheet_manager_id', '=', False),
            ])

            action = "delete" if delete else "modify" if vals is not None and "date" in vals else "create or edit"
            for line in self:
                show_access_error = False
                employee = line.employee_id
                company = line.company_id
                last_validated_timesheet_date = employee.sudo().last_validated_timesheet_date
                def is_wrong_date(date):
                    return date != fields.Date.today() and date <= last_validated_timesheet_date

                # When an user having this group tries to modify the timesheets of another user in his own team, we shouldn't raise any validation error
                if not is_timesheet_approver or employee not in employees:
                    if line.is_timesheet and last_validated_timesheet_date:
                        if action == "modify" and is_wrong_date(fields.Date.to_date(str(vals['date']))):
                            show_access_error = True
                        elif is_wrong_date(line.date):
                            show_access_error = True

                if show_access_error:
                    last_validated_timesheet_date_str = str(last_validated_timesheet_date.strftime('%m/%d/%Y'))
                    deleted = _('deleted')
                    modified = _('modified')
                    raise AccessError(_('Timesheets before the %s (included) have been validated, and can no longer be %s.', last_validated_timesheet_date_str, deleted if delete else modified))

    def _check_can_create(self):

        # Check if the user has the correct access to create timesheets
        if not (self.user_has_groups('hr_timesheet.group_hr_timesheet_approver') or self.env.su) and any(line.is_timesheet and line.user_id.id != self.env.user.id for line in self):
            raise AccessError(_("You cannot access timesheets that are not yours."))
        self.check_if_allowed()

        return super()._check_can_create()

    def _check_can_write(self, vals):
        if not self.user_has_groups('hr_timesheet.group_hr_timesheet_approver'):
            if 'validated' in vals:
                raise AccessError(_('You can only validate the timesheets of employees of whom you are the manager or the timesheet approver.'))
            elif self.filtered(lambda r: r.is_timesheet and r.validated):
                raise AccessError(_('Only a Timesheets Approver or Manager is allowed to modify a validated entry.'))

        self.check_if_allowed(vals)

        return super()._check_can_write(vals)

    @api.model
    def _get_timesheet_field_and_model_name(self):
        return 'task_id', 'project.task'

    @api.model
    def grid_update_cell(self, domain, measure_field_name, value):
        if value == 0:  # nothing to do
            return
        timesheets = self.search(domain, limit=2)

        # sudo in case of timesheeting a task belonging to a private project
        if timesheets.project_id and not all(timesheets.project_id.sudo().mapped("allow_timesheets")):
            raise UserError(_("You cannot adjust the time of the timesheet for a project with timesheets disabled."))

        non_validated_timesheets = timesheets.filtered(lambda timesheet: not timesheet.validated)
        if len(non_validated_timesheets) > 1 or (len(timesheets) == 1 and timesheets.validated):
            timesheets[0].copy({
                'name': '/',
                measure_field_name: value,
            })
        elif len(non_validated_timesheets) == 1:
            non_validated_timesheets[measure_field_name] += value
        else:
            project_id = self._context.get('default_project_id', False)
            field_name, model_name = self._get_timesheet_field_and_model_name()
            field_value = self._context.get(f'default_{field_name}', False)
            if not project_id and field_value:
                project_id = self.env[model_name].browse(field_value).project_id.id
            if not project_id:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': _("Your timesheet entry is missing a project. Please either group the Grid view by project or enter your timesheets through another view."),
                        'type': 'danger',
                        'sticky': False,
                    }
                }
            if not self.env['project.project'].browse(project_id).sudo().allow_timesheets:
                raise UserError(_("You cannot adjust the time of the timesheet for a project with timesheets disabled."))

            self.create({
                'name': '/',
                'project_id': project_id,
                field_name: field_value,
                measure_field_name: value,
            })

    @api.ondelete(at_uninstall=False)
    def _unlink_if_manager(self):
        if not self.user_has_groups('hr_timesheet.group_hr_timesheet_approver') and self.filtered(
                lambda r: r.is_timesheet and r.validated):
            raise AccessError(_('You cannot delete a validated entry. Please, contact your manager or your timesheet approver.'))

        self.check_if_allowed(delete=True)

    def unlink(self):
        res = super(AnalyticLine, self).unlink()
        self.env['timer.timer'].search([
            ('res_model', '=', self._name),
            ('res_id', 'in', self.ids)
        ]).unlink()
        return res

    @api.model
    def _apply_timesheet_label(self, view_arch, view_type='form'):
        doc = view_arch
        encoding_uom = self.env.company.timesheet_encode_uom_id
        # Here, we select only the unit_amount field having no string set to give priority to
        # custom inheretied view stored in database. Even if normally, no xpath can be done on
        # 'string' attribute.
        for node in doc.xpath("//field[@name='unit_amount'][@widget='timesheet_uom' or @widget='timesheet_uom_timer'][not(@string)]"):
            if view_type == 'grid':
                node.set('string', encoding_uom.name)
            else:
                node.set('string', _('%s Spent', re.sub(r'[\(\)]', '', encoding_uom.name or '')))
        return doc

    def _get_project_task_from_domain(self, domain):
        project_id = task_id = False
        for subdomain in domain:
            if subdomain[0] == 'project_id' and subdomain[1] == '=':
                project_id = subdomain[2]
            elif subdomain[0] == 'task_id' and subdomain[1] == '=':
                task_id = subdomain[2]
        return project_id, task_id

    def _prepare_duplicate_timesheet_line_values(self, column_field, day, cell_field, change):
        # Prepares all values that should be set/modified when duplicating the current analytic line
        return {
            'name': '/',
            column_field: day,
            cell_field: change,
        }

    def _group_expand_employee_ids(self, employees, domain, order):
        """ Group expand by employee_ids in grid view

            This group expand allow to add some record by employee, where
            the employee has been timesheeted in a task of a project in the
            past 7 days.

            Example: Filter timesheet from my team this week:
            [['project_id', '!=', False],
             '|',
                 ['employee_id.timesheet_manager_id', '=', 2],
                 '|',
                     ['employee_id.parent_id.user_id', '=', 2],
                     '|',
                         ['project_id.user_id', '=', 2],
                         ['user_id', '=', 2]]
             '&',
                 ['date', '>=', '2020-06-01'],
                 ['date', '<=', '2020-06-07']

            Becomes:
            [('project_id', '!=', False),
             ('date', '>=', datetime.date(2020, 5, 28)),
             ('date', '<=', '2020-06-04'),
             ['project_id', '!=', False],
             '|',
                 ['employee_id.timesheet_manager_id', '=', 2],
                 '|',
                    ['employee_id.parent_id.user_id', '=', 2],
                    '|',
                        ['project_id.user_id', '=', 2],
                        ['user_id', '=', 2]]
             '&',
                 ['date', '>=', '1970-01-01'],
                 ['date', '<=', '2250-01-01']
        """
        if not self.env.context.get('group_expand', False):
            return employees

        grid_anchor, last_week = self._get_last_week()
        domain_search = expression.AND([
            [('project_id.allow_timesheets', '=', True),
             ('date', '>=', last_week),
             ('date', '<=', grid_anchor),
             '|',
                ('task_id.active', '=', True),
                ('task_id', '=', False),
            ], filter_domain_leaf(domain, lambda field: field != 'date')
        ])

        group_order = self.env['hr.employee']._order
        if order == group_order:
            order = 'employee_id'
        elif order == tools.reverse_order(group_order):
            order = 'employee_id desc'
        else:
            order = None
        return self.search(domain_search, order=order).employee_id

    def _get_last_week(self):
        today = fields.Date.to_string(fields.Date.today())
        grid_anchor = self.env.context.get('grid_anchor', today)
        last_week = fields.Datetime.from_string(grid_anchor)
        last_week += relativedelta(weekday=SU(-2))
        return grid_anchor, last_week.date()
    # ----------------------------------------------------
    # Timer Methods
    # ----------------------------------------------------

    @api.model
    def action_start_new_timesheet_timer(self, vals):
        project = self.env['project.project'].browse(vals.get('project_id', False))
        if not project:
            task = self.env['project.task'].browse(vals.get('task_id', False))
            project = task.project_id or self.env['project.project'].browse(self._get_favorite_project_id())
        result = bool(project) and project.check_can_start_timer()
        if result is True:
            if "default_date" in self._context:
                self = self.with_context(default_date=fields.Date.today())
            timesheet = self.create({
                **vals,
                'project_id': project.id,
            })
            timesheet.action_timer_start()
            return timesheet._get_timesheet_timer_data()
        return result

    def action_timer_start(self):
        """ Action start the timer of current timesheet

            * Override method of hr_timesheet module.
        """
        if self.validated:
            raise UserError(_('You cannot use the timer on validated timesheets.'))
        if self.employee_id.sudo().last_validated_timesheet_date and self.date < self.employee_id.sudo().last_validated_timesheet_date:
            timesheet = self.create([{'project_id': self.project_id.id, 'task_id': self.task_id.id, 'date': datetime.today().date()}])
            timesheet.action_timer_start()
        elif not self.user_timer_id.timer_start and self.display_timer:
            if self.date != fields.Date.context_today(self):
                self.action_start_new_timesheet_timer({
                    'name': self.name,
                    'project_id': self.project_id.id,
                    'task_id': self.task_id.id,
                })
            else:
                super(AnalyticLine, self).action_timer_start()

    def _get_last_timesheet_domain(self):
        self.ensure_one()
        return [
            ('id', '!=', self.id),
            ('user_id', '=', self.env.user.id),
            ('project_id', '=', self.project_id.id),
            ('task_id', '=', self.task_id.id),
            ('date', '=', fields.Date.today()),
            ('name', '=', '/'),
            ('validated', '=', False),
        ]

    def _add_timesheet_time(self, minutes_spent, try_to_match=False):
        if self.unit_amount == 0 and not minutes_spent:
            # Check if unit_amount equals 0,
            # if yes, then remove the timesheet
            self.unlink()
            return 0
        minimum_duration = int(self.env['ir.config_parameter'].sudo().get_param('timesheet_grid.timesheet_min_duration', 0))
        rounding = int(self.env['ir.config_parameter'].sudo().get_param('timesheet_grid.timesheet_rounding', 0))
        minutes_spent = self._timer_rounding(minutes_spent, minimum_duration, rounding)
        amount = self.unit_amount + minutes_spent * 60 / 3600
        if not try_to_match or self.name != '/':
            self.write({'unit_amount': amount})
            return amount

        domain = self._get_last_timesheet_domain()
        last_timesheet_id = self.search(domain, limit=1)
        # If the last timesheet of the day for this project and task has no description,
        # we match both together.
        if last_timesheet_id:
            last_timesheet_id.unit_amount += amount
            self.unlink()
        else:
            self.write({'unit_amount': amount})
        return amount

    def action_timer_stop(self, try_to_match=False):
        """ Action stop the timer of the current timesheet
            try_to_match: if true, we try to match with another timesheet which corresponds to the following criteria:
            1. Neither of them has a description
            2. The last one is not validated
            3. Match user, project task, and must be the same day.

            * Override method of timer module.
        """
        if self.env.user == self.sudo().user_id:
            # sudo as we can have a timesheet related to a company other than the current one.
            self = self.sudo()
        if self.validated:
            raise UserError(_('You cannot use the timer on validated timesheets.'))
        amount = 0
        if self.user_timer_id.timer_start:
            minutes_spent = super(AnalyticLine, self).action_timer_stop()
            amount = self._add_timesheet_time(minutes_spent, try_to_match)
        return amount

    def _stop_all_users_timer(self, try_to_match=False):
        """ Stop ALL the timers of the timesheets (WHOEVER the timer associated user is)
            try_to_match: if true, we try to match with another timesheet which corresponds to the following criteria:
            1. Neither of them has a description
            2. The last one is not validated
            3. Match user, project task, and must be the same day.
        """
        if any(self.sudo().mapped('validated')):
            raise UserError(_('Sorry, you cannot use a timer for a validated timesheet'))
        timers = self.env['timer.timer'].sudo().search([('res_id', 'in', self.ids), ('res_model', '=', self._name)])
        for timer in timers:
            minutes_spent = timer.action_timer_stop()
            self.env["account.analytic.line"].browse(timer.res_id).sudo()._add_timesheet_time(minutes_spent, try_to_match)
            timer.unlink()

    def action_timer_unlink(self):
        """ Action unlink the timer of the current timesheet
        """
        if self.env.user == self.sudo().user_id:
            # sudo as we can have a timesheet related to a company other than the current one.
            self = self.sudo()
        self.user_timer_id.unlink()
        if not self.unit_amount:
            self.unlink()

    def _action_interrupt_user_timers(self):
        self.action_timer_stop()

    def _get_timesheet_timer_data(self, timer=None):
        if not timer:
            timer = self.user_timer_id
        running_seconds = (fields.Datetime.now() - timer.timer_start).total_seconds() + self.unit_amount * 3600
        data = {
            'id': timer.res_id,
            'start': running_seconds,
            'project_id': self.project_id.id,
            'task_id': self.task_id.id,
            'description': self.name,
        }
        if self.project_id.company_id and self.project_id.company_id not in self.env.companies:
            data.update({
                'readonly': True,
                'project_name': self.project_id.name,
                'task_name': self.task_id.name or '',
            })
        return data

    @api.model
    def get_running_timer(self):
        step_timer = int(self.env['ir.config_parameter'].sudo().get_param('timesheet_grid.timesheet_min_duration', 15))
        timer = self.env['timer.timer'].search([
            ('user_id', '=', self.env.user.id),
            ('timer_start', '!=', False),
            ('timer_pause', '=', False),
            ('res_model', '=', self._name),
        ], limit=1)
        if not timer:
            return {'step_timer': step_timer}

        # sudo as we can have a timesheet related to a company other than the current one.
        timer_data = self.sudo().browse(timer.res_id)._get_timesheet_timer_data(timer)
        timer_data['step_timer'] = step_timer
        return timer_data

    @api.model
    def get_rounded_time(self, timer):
        minimum_duration = int(self.env['ir.config_parameter'].sudo().get_param('timesheet_grid.timesheet_min_duration', 0))
        rounding = int(self.env['ir.config_parameter'].sudo().get_param('timesheet_grid.timesheet_rounding', 0))
        rounded_minutes = self._timer_rounding(timer, minimum_duration, rounding)
        return rounded_minutes / 60

    @api.model
    def _add_time_to_timesheet_fields(self):
        return ['task_id']

    def action_add_time_to_timesheet(self, vals):
        minutes = int(self.env['ir.config_parameter'].sudo().get_param('timesheet_grid.timesheet_min_duration', 15))
        if self:
            for field in self._add_time_to_timesheet_fields():
                val = vals.get(field, False)
                if self[field].id == val and self.project_id.id == vals['project_id']:
                    self.unit_amount += minutes / 60
                    return self.id
        timesheet = self.create({
            **vals,
            'unit_amount': minutes / 60,
        })
        return timesheet.id

    def action_add_time_to_timer(self, time):
        if self.validated:
            raise UserError(_('You cannot use the timer on validated timesheets.'))
        if not self.user_id.employee_ids:
            raise UserError(_('An employee must be linked to your user to record time.'))
        timer = self.user_timer_id
        if not timer:
            self.action_timer_start()
            timer = self.user_timer_id
        timer.timer_start = min(timer.timer_start - timedelta(0, time), fields.Datetime.now())

    def change_description(self, description):
        if not self.exists():
            return
        if True in self.mapped('validated'):
            raise UserError(_('You cannot use the timer on validated timesheets.'))
        self.write({'name': description})

    def action_change_project_task(self, new_project_id, new_task_id):
        if self.validated:
            raise UserError(_('You cannot use the timer on validated timesheets.'))
        if not self.unit_amount:
            self.write({
                'project_id': new_project_id,
                'task_id': new_task_id,
            })
            return self.id

        new_timesheet = self.create({
            'name': self.name,
            'project_id': new_project_id,
            'task_id': new_task_id,
        })
        self.user_timer_id.res_id = new_timesheet
        return new_timesheet.id

    def _action_open_to_validate_timesheet_view(self, type_view=None):
        action = self.env['ir.actions.act_window']._for_xml_id('timesheet_grid.timesheet_grid_to_validate_action')
        context = action.get('context', {}) and ast.literal_eval(action['context'])
        if (type_view == 'week'):
            context['grid_range'] = 'week'
            context['grid_anchor'] = fields.Date.today() - relativedelta(weeks=1)
        else:
            context['grid_range'] = 'month'
            if type_view == 'month':
                context['grid_anchor'] = fields.Date.today() - relativedelta(months=1)
            else:
                context['grid_anchor'] = fields.Date.today()
                context.pop('search_default_my_team_timesheet', None)

        if type_view in ('week', 'month'):
            action['view_mode'] = ','.join([
                mode
                for mode in action['view_mode'].split(",")
                if mode != "pivot"
            ])
            action['views'] = [
                view
                for view in action['views']
                if view[1] != "pivot"
            ]
        action['context'] = context
        return action

    def _get_domain_for_validation_timesheets(self, validated=False):
        """ Get the domain to check if the user can validate/invalidate which timesheets

            2 access rights give access to validate timesheets:

            1. Approver: in this access right, the user can't validate all timesheets,
            he can validate the timesheets where he is the manager or timesheet responsible of the
            employee who is assigned to this timesheets or the user is the owner of the project.
            The user cannot validate his own timesheets.

            2. Manager (Administrator): with this access right, the user can validate all timesheets.
        """
        domain = [('is_timesheet', '=', True), ('validated', '=', validated)]
        if not validated:
            domain = expression.AND([
                domain,
                [("date", "<=", fields.Date.today())],
            ])

        if not self.user_has_groups('hr_timesheet.group_timesheet_manager'):
            return expression.AND([
                domain,
                [
                    ('user_id', '!=', self._uid),
                    '|', ('employee_id.timesheet_manager_id', '=', self._uid),
                    '|', ('employee_id', 'in', self.env.user.employee_id.subordinate_ids.ids),
                    '|', ('employee_id.parent_id.user_id', '=', self._uid),
                    '&', ('employee_id.timesheet_manager_id', '=', False), ('employee_id.parent_id', '=', False),
                ],
            ])
        return domain

    def _get_timesheets_to_merge(self):
        return self.filtered(lambda l: l.is_timesheet and not l.validated)

    def action_merge_timesheets(self):
        to_merge = self._get_timesheets_to_merge()

        if len(to_merge) <= 1:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _('There are no timesheets to merge.'),
                    'type': 'warning',
                    'sticky': False,
                }
            }

        return {
            'name': _('Merge Timesheets'),
            'view_mode': 'form',
            'res_model': 'hr_timesheet.merge.wizard',
            'views': [(self.env.ref('timesheet_grid.timesheet_merge_wizard_view_form').id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': dict(self.env.context, active_ids=to_merge.ids),
        }

    def action_timer_increase(self):
        min_duration = int(self.env['ir.config_parameter'].sudo().get_param('timesheet_grid.timesheet_min_duration', 0))
        self.update({'unit_amount': self.unit_amount + (min_duration / 60)})

    def action_timer_decrease(self):
        min_duration = int(self.env['ir.config_parameter'].sudo().get_param('timesheet_grid.timesheet_min_duration', 0))
        duration = self.unit_amount - (min_duration / 60)
        self.update({'unit_amount': duration if duration > 0 else 0 })
