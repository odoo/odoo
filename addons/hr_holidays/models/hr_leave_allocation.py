# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (c) 2005-2006 Axelor SARL. (http://www.axelor.com)

import logging

import pytz

from datetime import datetime, time
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _

from odoo.addons.resource.models.resource import HOURS_PER_DAY

_logger = logging.getLogger(__name__)


class HolidaysAllocation(models.Model):
    """
        Here are the rights associated with the flow of allocation requests

        State       Groups              Restriction
        ============================================================================================================
        Draft       Anybody             Own Allocation only and state in [confirm, refuse]
                    Holiday Manager     State in [confirm, refuse]
        Confirm     All                 State = draft
        Validate1   Holiday Officer     Not his own Allocation and state = confirm
                    Holiday Manager     Not his own Allocation or has no manager and State = confirm
        Validate    Holiday Officer     Not his own Allocation and state = confirm
                    Holiday Manager     Not his own Allocation or has no manager and State in [validate1, confirm]
        Refuse      Holiday Officer     State in [confirm, validate, validate1]
                    Holiday Manager     State in [confirm, validate, validate1]
        ============================================================================================================
    """
    _name = "hr.leave.allocation"
    _description = "Leaves Allocation"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    def _default_domain_holiday_status_id(self):
        if self.user_has_groups('hr_holidays.group_hr_holidays_manager'):
            return [('valid', '=', True), ('limit', '=', False)]
        return [('valid', '=', True), ('employee_applicability', 'in', ['allocation', 'both']), ('limit', '=', False)]

    def _default_employee(self):
        return self.env.context.get('default_employee_id') or self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)

    def _default_holiday_status_id(self):
        LeaveType = self.env['hr.leave.type'].with_context(employee_id=self._default_employee().id)
        lt = LeaveType.search(self._default_domain_holiday_status_id())
        return lt[:1]

    name = fields.Char('Description')
    state = fields.Selection([
        ('draft', 'To Submit'),
        ('cancel', 'Cancelled'),
        ('confirm', 'To Approve'),
        ('refuse', 'Refused'),
        ('validate1', 'Second Approval'),
        ('validate', 'Approved')
        ], string='Status', readonly=True, track_visibility='onchange', copy=False, default='confirm',
            help="The status is set to 'To Submit', when a leave request is created." +
            "\nThe status is 'To Approve', when leave request is confirmed by user." +
            "\nThe status is 'Refused', when leave request is refused by manager." +
            "\nThe status is 'Approved', when leave request is approved by manager.")
    date_from = fields.Datetime('Start Date', readonly=True, index=True, copy=False,
        states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]}, track_visibility='onchange')
    date_to = fields.Datetime('End Date', readonly=True, copy=False,
        states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]}, track_visibility='onchange')
    holiday_status_id = fields.Many2one("hr.leave.type", string="Leave Type", required=True, readonly=True,
        states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]},
        domain=lambda self: self._default_domain_holiday_status_id(), default=_default_holiday_status_id)
    employee_id = fields.Many2one('hr.employee', string='Employee', index=True, readonly=True,
        states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]}, default=_default_employee, track_visibility='onchange')
    notes = fields.Text('Reasons', readonly=True, states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    number_of_days_temp = fields.Float(
        'Duration (days)', copy=False, readonly=True,
        states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]},
        help='Number of days of the leave request according to your working schedule.')
    number_of_days = fields.Float('Number of Days', compute='_compute_number_of_days', store=True, track_visibility='onchange')
    number_of_hours = fields.Float('Duration (hours)', help="Number of hours of the leave allocation according to your working schedule.")
    parent_id = fields.Many2one('hr.leave.allocation', string='Parent')
    linked_request_ids = fields.One2many('hr.leave.allocation', 'parent_id', string='Linked Requests')
    department_id = fields.Many2one('hr.department', string='Department', readonly=True, states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    category_id = fields.Many2one('hr.employee.category', string='Employee Tag', readonly=True,
        states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]}, help='Category of Employee')
    holiday_type = fields.Selection([
        ('employee', 'By Employee'),
        ('department', 'By Department'),
        ('category', 'By Employee Tag')
    ], string='Allocation Mode', readonly=True, required=True, default='employee',
        states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]},
        help='By Employee: Allocation for individual Employee, By Employee Tag: Allocation for group of employees in category')
    first_approver_id = fields.Many2one('hr.employee', string='First Approval', readonly=True, copy=False,
        help='This area is automatically filled by the user who validate the leave', oldname='manager_id')
    second_approver_id = fields.Many2one('hr.employee', string='Second Approval', readonly=True, copy=False, oldname='manager_id2',
        help='This area is automaticly filled by the user who validate the leave with second level (If Leave type need second validation)')
    validation_type = fields.Selection('Validation Type', related='holiday_status_id.validation_type')
    can_reset = fields.Boolean('Can reset', compute='_compute_can_reset')
    can_approve = fields.Boolean('Can Approve', compute='_compute_can_approve')
    type_request_unit = fields.Selection(related='holiday_status_id.request_unit')
    accrual = fields.Boolean("Accrual", related='holiday_status_id.accrual', store=True, readonly=True)
    number_per_interval = fields.Float("Number of unit per interval", readonly=True, states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]}, default=1)
    interval_number = fields.Integer("Number of unit between two intervals", readonly=True, states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]}, default=1)
    unit_per_interval = fields.Selection([
        ('hours', 'Hour(s)'),
        ('days', 'Day(s)')
        ], string="Unit of time added at each interval", default='hours', readonly=True, states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    interval_unit = fields.Selection([
        ('weeks', 'Week(s)'),
        ('months', 'Month(s)'),
        ('years', 'Year(s)')
        ], string="Unit of time between two intervals", default='weeks', readonly=True, states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    nextcall = fields.Date("Date of the next accrual allocation", default=False, readonly=True)

    _sql_constraints = [
        ('type_value', "CHECK( (holiday_type='employee' AND employee_id IS NOT NULL) or (holiday_type='category' AND category_id IS NOT NULL) or (holiday_type='department' AND department_id IS NOT NULL) )",
         "The employee, department or employee category of this request is missing. Please make sure that your user login is linked to an employee."),
        ('date_check', "CHECK ( number_of_days_temp >= 0 )", "The number of days must be greater than 0."),
        ('number_per_interval_check', "CHECK(number_per_interval > 0)", "The number per interval should be greater than 0"),
        ('interval_number_check', "CHECK(interval_number > 0)", "The interval number should be greater than 0"),
    ]

    @api.model
    def _update_accrual(self):
        """
            Method called by the cron task in order to increment the number_of_days when
            necessary.
        """
        today = fields.Date.from_string(fields.Date.today())

        holidays = self.search([('accrual', '=', True), ('state', '=', 'validate'),
                                '|', ('date_to', '=', False), ('date_to', '>', fields.Datetime.now()),
                                '|', ('nextcall', '=', False), ('nextcall', '<=', today)])

        for holiday in holidays:
            values = {}

            delta = relativedelta(days=0)

            if holiday.interval_unit == 'weeks':
                delta = relativedelta(weeks=holiday.interval_number)
            if holiday.interval_unit == 'months':
                delta = relativedelta(months=holiday.interval_number)
            if holiday.interval_unit == 'years':
                delta = relativedelta(years=holiday.interval_number)

            values['nextcall'] = (holiday.nextcall if holiday.nextcall else today) + delta

            period_start = datetime.combine(today, time(0, 0, 0)) - delta
            period_end = datetime.combine(today, time(0, 0, 0))

            # We have to check when the employee has been created
            # in order to not allocate him/her too much leaves
            creation_date = fields.Datetime.from_string(holiday.employee_id.create_date)

            # If employee is created after the period, we cancel the computation
            if period_end <= creation_date:
                holiday.write(values)
                continue

            # If employee created during the period, taking the date at which he has been created
            if period_start <= creation_date:
                period_start = creation_date

            worked = holiday.employee_id.get_work_days_data(period_start, period_end, domain=[('holiday_id.holiday_status_id.unpaid', '=', True), ('time_type', '=', 'leave')])['days']
            left = holiday.employee_id.get_leave_days_data(period_start, period_end, domain=[('holiday_id.holiday_status_id.unpaid', '=', True), ('time_type', '=', 'leave')])['days']
            prorata = worked / (left + worked) if worked else 0

            days_to_give = holiday.number_per_interval
            if holiday.unit_per_interval == 'hours':
                # As we encode everything in days in the database we need to convert
                # the number of hours into days for this we use the
                # mean number of hours set on the employee's calendar
                days_to_give = days_to_give / holiday.employee_id.resource_calendar_id.hours_per_day or HOURS_PER_DAY

            values['number_of_days_temp'] = holiday.number_of_days_temp + days_to_give * prorata

            if holiday.holiday_status_id.balance_limit > 0:
                values['number_of_days_temp'] = min(values['number_of_days_temp'], holiday.holiday_status_id.balance_limit)

            values['number_of_hours'] = values['number_of_days_temp'] * holiday.employee_id.resource_calendar_id.hours_per_day or HOURS_PER_DAY

            holiday.write(values)

    @api.multi
    @api.depends('number_of_days_temp', 'type_request_unit', 'number_of_hours', 'holiday_status_id', 'employee_id')
    def _compute_number_of_days(self):
        for holiday in self:
            number_of_days = holiday.number_of_days_temp
            if holiday.type_request_unit == 'hour':
                # In this case we need the number of days to reflect the number of hours taken
                number_of_days = holiday.number_of_hours / holiday.employee_id.resource_calendar_id.hours_per_day or HOURS_PER_DAY
            if holiday.holiday_status_id.balance_limit > 0:
                number_of_days = min(number_of_days, holiday.holiday_status_id.balance_limit)

            holiday.number_of_days = number_of_days

    @api.multi
    def _compute_can_reset(self):
        """ User can reset a leave request if it is its own leave request
            or if he is an Hr Manager.
        """
        user = self.env.user
        group_hr_manager = self.env.ref('hr_holidays.group_hr_holidays_manager')
        for holiday in self:
            if group_hr_manager in user.groups_id or holiday.employee_id and holiday.employee_id.user_id == user:
                holiday.can_reset = True

    @api.depends('employee_id', 'department_id')
    def _compute_can_approve(self):
        """ User can only approve a leave request if it is not his own
            Exception : User is holiday manager and has no manager
        """
        for holiday in self:
            # User is holiday manager and has no manager
            manager = self.user_has_groups('hr_holidays.group_hr_holidays_manager')
            holiday.can_approve = (holiday.employee_id.user_id.id != self.env.uid) or manager

    @api.onchange('holiday_type')
    def _onchange_type(self):
        if self.holiday_type == 'employee' and not self.employee_id:
            if self.env.user.employee_ids:
                self.employee_id = self.env.user.employee_ids[0]
        elif self.holiday_type == 'department':
            if self.env.user.employee_ids:
                self.department_id = self.department_id or self.env.user.employee_ids[0].department_id
            self.employee_id = None
        elif self.holiday_type == 'category':
            self.employee_id = None
            self.department_id = None

    @api.onchange('employee_id')
    def _onchange_employee(self):
        if self.holiday_type == 'employee':
            self.department_id = self.employee_id.department_id

    @api.onchange('number_of_days_temp')
    def _onchange_number_of_days_temp(self):
        self.number_of_hours = self.number_of_days_temp * self.employee_id.resource_calendar_id.hours_per_day

    @api.onchange('number_of_hours')
    def _onchange_number_of_hours(self):
        self.number_of_days_temp = self.number_of_hours / self.employee_id.resource_calendar_id.hours_per_day

    @api.onchange('holiday_status_id')
    def _onchange_holiday_status_id(self):
        self.date_to = datetime.combine(self.holiday_status_id.validity_stop, time.max)

        if self.accrual:
            self.number_of_days_temp = 0

            if self.holiday_status_id.request_unit == 'hour':
                self.unit_per_interval = 'hours'
            else:
                self.unit_per_interval = 'days'
        else:
            self.interval_number = 1
            self.interval_unit = 'weeks'
            self.number_per_interval = 1
            self.unit_per_interval = 'hours'

    ####################################################
    # ORM Overrides methods
    ####################################################

    @api.multi
    def name_get(self):
        res = []
        for leave in self:
            if leave.type_request_unit == 'hour':
                res.append((leave.id, _("Allocation of %s : %.2f hour(s) To %s") % (leave.holiday_status_id.name, leave.number_of_hours, leave.employee_id.name)))
            else:
                res.append((leave.id, _("Allocation of %s : %.2f day(s) To %s") % (leave.holiday_status_id.name, leave.number_of_days_temp, leave.employee_id.name)))
        return res

    @api.multi
    def add_follower(self, employee_id):
        employee = self.env['hr.employee'].browse(employee_id)
        if employee.user_id:
            self.message_subscribe(partner_ids=employee.user_id.partner_id.ids)

    @api.multi
    @api.constrains('holiday_status_id')
    def _check_leave_type_validity(self):
        for allocation in self:
            if allocation.holiday_status_id.validity_start and allocation.holiday_status_id.validity_stop:
                vstart = allocation.holiday_status_id.validity_start
                vstop = allocation.holiday_status_id.validity_stop
                today = fields.Date.today()

                if vstart > today or vstop < today:
                    raise UserError(_('You can allocate %s only between %s and %s') % (allocation.holiday_status_id.display_name,
                                                                                  allocation.holiday_status_id.validity_start, allocation.holiday_status_id.validity_stop))

    @api.model
    def create(self, values):
        """ Override to avoid automatic logging of creation """
        if values.get('accrual', False):
            values['date_from'] = fields.Datetime.now()
        employee_id = values.get('employee_id', False)
        if not values.get('department_id'):
            values.update({'department_id': self.env['hr.employee'].browse(employee_id).department_id.id})
        holiday = super(HolidaysAllocation, self.with_context(mail_create_nolog=True, mail_create_nosubscribe=True)).create(values)
        holiday.add_follower(employee_id)
        holiday.activity_update()
        return holiday

    @api.multi
    def write(self, values):
        employee_id = values.get('employee_id', False)
        result = super(HolidaysAllocation, self).write(values)
        self.add_follower(employee_id)
        return result

    @api.multi
    def unlink(self):
        for holiday in self.filtered(lambda holiday: holiday.state not in ['draft', 'cancel', 'confirm']):
            raise UserError(_('You cannot delete a leave which is in %s state.') % (holiday.state,))
        return super(HolidaysAllocation, self).unlink()

    @api.multi
    def copy_data(self, default=None):
        raise UserError(_('A leave cannot be duplicated.'))

    ####################################################
    # Business methods
    ####################################################

    @api.multi
    def _prepare_holiday_values(self, employee):
        self.ensure_one()
        values = {
            'name': self.name,
            'holiday_type': 'employee',
            'holiday_status_id': self.holiday_status_id.id,
            'notes': self.notes,
            'number_of_days_temp': self.number_of_days_temp,
            'parent_id': self.id,
            'employee_id': employee.id
        }
        return values

    @api.multi
    def action_draft(self):
        for holiday in self:
            if not holiday.can_reset:
                raise UserError(_('Only an HR Manager or the concerned employee can reset to draft.'))
            if holiday.state not in ['confirm', 'refuse']:
                raise UserError(_('Leave request state must be "Refused" or "To Approve" in order to reset to Draft.'))
            holiday.write({
                'state': 'draft',
                'first_approver_id': False,
                'second_approver_id': False,
            })
            linked_requests = holiday.mapped('linked_request_ids')
            for linked_request in linked_requests:
                linked_request.action_draft()
            linked_requests.unlink()
        self.activity_update()
        return True

    @api.multi
    def action_confirm(self):
        if self.filtered(lambda holiday: holiday.state != 'draft'):
            raise UserError(_('Leave request must be in Draft state ("To Submit") in order to confirm it.'))
        res = self.write({'state': 'confirm'})
        self.activity_update()
        return res

    @api.multi
    def action_approve(self):
        # if validation_type == 'both': this method is the first approval approval
        # if validation_type != 'both': this method calls action_validate() below
        if not self.env.user.has_group('hr_holidays.group_hr_holidays_user'):
            raise UserError(_('Only an HR Officer or Manager can approve leave requests.'))

        current_employee = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
        if any(holiday.state != 'confirm' for holiday in self):
            raise UserError(_('Leave request must be confirmed ("To Approve") in order to approve it.'))

        for holiday in self:
            validation_type = holiday.holiday_status_id.validation_type
            manager = holiday.employee_id.parent_id or holiday.employee_id.department_id.manager_id
            if (validation_type in ['hr', 'both']) and (manager and manager != current_employee)\
              and not self.env.user.has_group('hr_holidays.group_hr_holidays_manager'):
                raise UserError(_('You must be %s manager to approve this leave') % (holiday.employee_id.name))
            elif validation_type == 'manager' and not self.env.user.has_group('hr_holidays.group_hr_holidays_manager'):
                raise UserError(_('You must be a Human Resource Manager to approve this Leave.'))

        self.filtered(lambda hol: hol.validation_type == 'both').write({'state': 'validate1', 'first_approver_id': current_employee.id})
        self.filtered(lambda hol: not hol.validation_type == 'both').action_validate()
        self.activity_update()
        return True

    @api.multi
    def action_validate(self):
        if not self.env.user.has_group('hr_holidays.group_hr_holidays_user'):
            raise UserError(_('Only an HR Officer or Manager can approve leave requests.'))

        if any(not holiday.can_approve for holiday in self):
            raise UserError(_('Only your manager can approve your allocations'))

        current_employee = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
        for holiday in self:
            if holiday.state not in ['confirm', 'validate1']:
                raise UserError(_('Leave request must be confirmed in order to approve it.'))
            if holiday.state == 'validate1' and not holiday.env.user.has_group('hr_holidays.group_hr_holidays_manager'):
                raise UserError(_('Only an HR Manager can apply the second approval on leave requests.'))

            holiday.write({'state': 'validate'})
            if holiday.validation_type == 'both':
                holiday.write({'second_approver_id': current_employee.id})
            else:
                holiday.write({'first_approver_id': current_employee.id})
            if holiday.holiday_type in ['category', 'department']:
                leaves = self.env['hr.leave.allocation']
                employees = holiday.category_id.employee_ids if holiday.holiday_type == 'category' else holiday.department_id.member_ids
                for employee in employees:
                    values = holiday._prepare_holiday_values(employee)
                    leaves += self.with_context(mail_notify_force_send=False).create(values)
                # TODO is it necessary to interleave the calls?
                leaves.action_approve()
                if leaves and leaves[0].validation_type == 'both':
                    leaves.action_validate()
        self.activity_update()
        return True

    @api.multi
    def action_refuse(self):
        if not self.env.user.has_group('hr_holidays.group_hr_holidays_user'):
            raise UserError(_('Only an HR Officer or Manager can refuse leave requests.'))

        current_employee = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
        for holiday in self:
            if holiday.state not in ['confirm', 'validate', 'validate1']:
                raise UserError(_('Leave request must be confirmed or validated in order to refuse it.'))

            if holiday.state == 'validate1':
                holiday.write({'state': 'refuse', 'first_approver_id': current_employee.id})
            else:
                holiday.write({'state': 'refuse', 'second_approver_id': current_employee.id})
            # If a category that created several holidays, cancel all related
            holiday.linked_request_ids.action_refuse()
        self.activity_update()
        return True

    # ------------------------------------------------------------
    # Activity methods
    # ------------------------------------------------------------

    def _get_responsible_for_approval(self):
        if self.state == 'confirm' and self.employee_id.parent_id.user_id:
            return self.employee_id.parent_id.user_id
        elif self.department_id.manager_id.user_id:
            return self.department_id.manager_id.user_id
        return self.env.user

    def activity_update(self):
        to_clean, to_do = self.env['hr.leave.allocation'], self.env['hr.leave.allocation']
        for allocation in self:
            if allocation.state == 'draft':
                to_clean |= allocation
            elif allocation.state == 'confirm':
                allocation.activity_schedule(
                    'hr_holidays.mail_act_leave_allocation_approval',
                    user_id=allocation.sudo()._get_responsible_for_approval().id)
            elif allocation.state == 'validate1':
                allocation.activity_feedback(['hr_holidays.mail_act_leave_allocation_approval'])
                allocation.activity_schedule(
                    'hr_holidays.mail_act_leave_allocation_second_approval',
                    user_id=allocation.sudo()._get_responsible_for_approval().id)
            elif allocation.state == 'validate':
                to_do |= allocation
            elif allocation.state == 'refuse':
                to_clean |= allocation
        if to_clean:
            to_clean.activity_unlink(['hr_holidays.mail_act_leave_allocation_approval', 'hr_holidays.mail_act_leave_allocation_second_approval'])
        if to_do:
            to_do.activity_feedback(['hr_holidays.mail_act_leave_allocation_approval', 'hr_holidays.mail_act_leave_allocation_second_approval'])

    ####################################################
    # Messaging methods
    ####################################################

    @api.multi
    def _track_subtype(self, init_values):
        if 'state' in init_values and self.state == 'validate':
            return 'hr_holidays.mt_leave_allocation_approved'
        elif 'state' in init_values and self.state == 'refuse':
            return 'hr_holidays.mt_leave_allocation_refused'
        return super(HolidaysAllocation, self)._track_subtype(init_values)

    @api.multi
    def _notify_get_groups(self, message, groups):
        """ Handle HR users and officers recipients that can validate or refuse holidays
        directly from email. """
        groups = super(HolidaysAllocation, self)._notify_get_groups(message, groups)

        self.ensure_one()
        hr_actions = []
        if self.state == 'confirm':
            app_action = self._notify_get_action_link('controller', controller='/allocation/validate')
            hr_actions += [{'url': app_action, 'title': _('Approve')}]
        if self.state in ['confirm', 'validate', 'validate1']:
            ref_action = self._notify_get_action_link('controller', controller='/allocation/refuse')
            hr_actions += [{'url': ref_action, 'title': _('Refuse')}]

        holiday_user_group_id = self.env.ref('hr_holidays.group_hr_holidays_user').id
        new_group = (
            'group_hr_holidays_user', lambda pdata: pdata['type'] == 'user' and holiday_user_group_id in pdata['groups'], {
                'actions': hr_actions,
            })

        return [new_group] + groups

    @api.multi
    def message_subscribe(self, partner_ids=None, channel_ids=None, subtype_ids=None):
        # due to record rule can not allow to add follower and mention on validated leave so subscribe through sudo
        if self.state in ['validate', 'validate1']:
            self.check_access_rights('read')
            self.check_access_rule('read')
            return super(HolidaysAllocation, self.sudo()).message_subscribe(partner_ids=partner_ids, channel_ids=channel_ids, subtype_ids=subtype_ids)
        return super(HolidaysAllocation, self).message_subscribe(partner_ids=partner_ids, channel_ids=channel_ids, subtype_ids=subtype_ids)
