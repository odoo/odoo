# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (c) 2005-2006 Axelor SARL. (http://www.axelor.com)

import logging
import math

from collections import namedtuple

from datetime import datetime, time
from pytz import timezone, UTC

from odoo import api, fields, models
from odoo.addons.base.models.res_partner import _tz_get
from odoo.addons.resource.models.resource import float_to_time, HOURS_PER_DAY
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools import float_compare
from odoo.tools.float_utils import float_round
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)

# Used to agglomerate the attendances in order to find the hour_from and hour_to
# See _onchange_request_parameters
DummyAttendance = namedtuple('DummyAttendance', 'hour_from, hour_to, dayofweek, day_period')

class HolidaysRequest(models.Model):
    """ Leave Requests Access specifications

     - a regular employee / user
      - can see all leaves;
      - cannot see name field of leaves belonging to other user as it may contain
        private information that we don't want to share to other people than
        HR people;
      - can modify only its own not validated leaves (except writing on state to
        bypass approval);
      - can discuss on its leave requests;
      - can reset only its own leaves;
      - cannot validate any leaves;
     - an Officer
      - can see all leaves;
      - can validate "HR" single validation leaves from people if
       - he is the employee manager;
       - he is the department manager;
       - he is member of the same department;
       - target employee has no manager and no department manager;
      - can validate "Manager" single validation leaves from people if
       - he is the employee manager;
       - he is the department manager;
       - target employee has no manager and no department manager;
      - can first validate "Both" double validation leaves from people like "HR"
        single validation, moving the leaves to validate1 state;
      - cannot validate its own leaves;
      - can reset only its own leaves;
      - can refuse all leaves;
     - a Manager
      - can do everything he wants

    On top of that multicompany rules apply based on company defined on the
    leave request leave type.
    """
    _name = "hr.leave"
    _description = "Leave"
    _order = "date_from desc"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _mail_post_access = 'read'

    @api.model
    def default_get(self, fields_list):
        defaults = super(HolidaysRequest, self).default_get(fields_list)
        defaults = self._default_get_request_parameters(defaults)

        LeaveType = self.env['hr.leave.type'].with_context(employee_id=defaults.get('employee_id'), default_date_from=defaults.get('date_from', fields.Datetime.now()))
        lt = LeaveType.search([('valid', '=', True)])

        defaults['holiday_status_id'] = lt[0].id if len(lt) > 0 else defaults.get('holiday_status_id')
        return defaults

    def _default_employee(self):
        return self.env.context.get('default_employee_id') or self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)

    def _default_get_request_parameters(self, values):
        new_values = dict(values)
        global_from, global_to = False, False
        # TDE FIXME: consider a mapping on several days that is not the standard
        # calendar widget 7-19 in user's TZ is some custom input
        if values.get('date_from'):
            user_tz = self.env.user.tz or 'UTC'
            localized_dt = timezone('UTC').localize(values['date_from']).astimezone(timezone(user_tz))
            global_from = localized_dt.time().hour == 7 and localized_dt.time().minute == 0
            new_values['request_date_from'] = values['date_from'].date()
        if values.get('date_to'):
            user_tz = self.env.user.tz or 'UTC'
            localized_dt = timezone('UTC').localize(values['date_to']).astimezone(timezone(user_tz))
            global_to = localized_dt.time().hour == 19 and localized_dt.time().minute == 0
            new_values['request_date_to'] = values['date_to'].date()
        if global_from and global_to:
            new_values['request_unit_custom'] = True
        return new_values

    # description
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
    payslip_status = fields.Boolean('Reported in last payslips', help='Green this button when the leave has been taken into account in the payslip.')
    report_note = fields.Text('HR Comments')
    user_id = fields.Many2one('res.users', string='User', related='employee_id.user_id', related_sudo=True, compute_sudo=True, store=True, default=lambda self: self.env.uid, readonly=True)
    # leave type configuration
    holiday_status_id = fields.Many2one(
        "hr.leave.type", string="Leave Type", required=True, readonly=True,
        states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]},
        domain=[('valid', '=', True)])
    validation_type = fields.Selection('Validation Type', related='holiday_status_id.validation_type', readonly=False)
    # HR data
    employee_id = fields.Many2one(
        'hr.employee', string='Employee', index=True, readonly=True,
        states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]}, default=_default_employee, track_visibility='onchange')
    tz_mismatch = fields.Boolean(compute='_compute_tz_mismatch')
    tz = fields.Selection(_tz_get, compute='_compute_tz')
    manager_id = fields.Many2one('hr.employee', string='Manager', readonly=True)
    department_id = fields.Many2one(
        'hr.department', string='Department', readonly=True,
        states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    notes = fields.Text('Reasons', readonly=True, states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    # duration
    date_from = fields.Datetime(
        'Start Date', readonly=True, index=True, copy=False, required=True,
        default=fields.Datetime.now,
        states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]}, track_visibility='onchange')
    date_to = fields.Datetime(
        'End Date', readonly=True, copy=False, required=True,
        default=fields.Datetime.now,
        states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]}, track_visibility='onchange')
    number_of_days = fields.Float(
        'Duration (Days)', copy=False, readonly=True, track_visibility='onchange',
        states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]},
        help='Number of days of the leave request according to your working schedule.')
    number_of_days_display = fields.Float(
        'Duration in days', compute='_compute_number_of_days_display', copy=False, readonly=True,
        help='Number of days of the leave request. Used for interface.')
    number_of_hours_display = fields.Float(
        'Duration in hours', compute='_compute_number_of_hours_display', copy=False, readonly=True,
        help='Number of hours of the leave request according to your working schedule. Used for interface.')
    duration_display = fields.Char('Requested (Days/Hours)', compute='_compute_duration_display',
        help="Field allowing to see the leave request duration in days or hours depending on the leave_type_request_unit")    # details
    # details
    meeting_id = fields.Many2one('calendar.event', string='Meeting')
    parent_id = fields.Many2one('hr.leave', string='Parent', copy=False)
    linked_request_ids = fields.One2many('hr.leave', 'parent_id', string='Linked Requests')
    holiday_type = fields.Selection([
        ('employee', 'By Employee'),
        ('company', 'By Company'),
        ('department', 'By Department'),
        ('category', 'By Employee Tag')],
        string='Allocation Mode', readonly=True, required=True, default='employee',
        states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]},
        help='By Employee: Allocation/Request for individual Employee, By Employee Tag: Allocation/Request for group of employees in category')
    category_id = fields.Many2one(
        'hr.employee.category', string='Employee Tag', readonly=True,
        states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]}, help='Category of Employee')
    mode_company_id = fields.Many2one(
        'res.company', string='Company', readonly=True,
        states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    first_approver_id = fields.Many2one(
        'hr.employee', string='First Approval', readonly=True, copy=False,
        help='This area is automatically filled by the user who validate the leave', oldname='manager_id')
    second_approver_id = fields.Many2one(
        'hr.employee', string='Second Approval', readonly=True, copy=False, oldname='manager_id2',
        help='This area is automaticly filled by the user who validate the leave with second level (If Leave type need second validation)')
    can_reset = fields.Boolean('Can reset', compute='_compute_can_reset')
    can_approve = fields.Boolean('Can Approve', compute='_compute_can_approve')

    # UX fields
    leave_type_request_unit = fields.Selection(related='holiday_status_id.request_unit', readonly=True)
    # Interface fields used when not using hour-based computation
    request_date_from = fields.Date('Request Start Date')
    request_date_to = fields.Date('Request End Date')
    # Interface fields used when using hour-based computation
    #
    # HACK We define the .5 hours as negative integers in order to
    # facilitate the migration to a better model later as we cannot
    # change the column type in stable and it was defined as an int4 column
    #
    request_hour_from = fields.Selection([
        (0, '12:00 AM'), (-1, '0:30 AM'),
        (1, '1:00 AM'), (-2, '1:30 AM'),
        (2, '2:00 AM'), (-3, '2:30 AM'),
        (3, '3:00 AM'), (-4, '3:30 AM'),
        (4, '4:00 AM'), (-5, '4:30 AM'),
        (5, '5:00 AM'), (-6, '5:30 AM'),
        (6, '6:00 AM'), (-7, '6:30 AM'),
        (7, '7:00 AM'), (-8, '7:30 AM'),
        (8, '8:00 AM'), (-9, '8:30 AM'),
        (9, '9:00 AM'), (-10, '9:30 AM'),
        (10, '10:00 AM'), (-11, '10:30 AM'),
        (11, '11:00 AM'), (-12, '11:30 AM'),
        (12, '12:00 PM'), (-13, '0:30 PM'),
        (13, '1:00 PM'), (-14, '1:30 PM'),
        (14, '2:00 PM'), (-15, '2:30 PM'),
        (15, '3:00 PM'), (-16, '3:30 PM'),
        (16, '4:00 PM'), (-17, '4:30 PM'),
        (17, '5:00 PM'), (-18, '5:30 PM'),
        (18, '6:00 PM'), (-19, '6:30 PM'),
        (19, '7:00 PM'), (-20, '7:30 PM'),
        (20, '8:00 PM'), (-21, '8:30 PM'),
        (21, '9:00 PM'), (-22, '9:30 PM'),
        (22, '10:00 PM'), (-23, '10:30 PM'),
        (23, '11:00 PM'), (-24, '11:30 PM')], string='Hour from')
    request_hour_to = fields.Selection([
        (0, '12:00 AM'), (-1, '0:30 AM'),
        (1, '1:00 AM'), (-2, '1:30 AM'),
        (2, '2:00 AM'), (-3, '2:30 AM'),
        (3, '3:00 AM'), (-4, '3:30 AM'),
        (4, '4:00 AM'), (-5, '4:30 AM'),
        (5, '5:00 AM'), (-6, '5:30 AM'),
        (6, '6:00 AM'), (-7, '6:30 AM'),
        (7, '7:00 AM'), (-8, '7:30 AM'),
        (8, '8:00 AM'), (-9, '8:30 AM'),
        (9, '9:00 AM'), (-10, '9:30 AM'),
        (10, '10:00 AM'), (-11, '10:30 AM'),
        (11, '11:00 AM'), (-12, '11:30 AM'),
        (12, '12:00 PM'), (-13, '0:30 PM'),
        (13, '1:00 PM'), (-14, '1:30 PM'),
        (14, '2:00 PM'), (-15, '2:30 PM'),
        (15, '3:00 PM'), (-16, '3:30 PM'),
        (16, '4:00 PM'), (-17, '4:30 PM'),
        (17, '5:00 PM'), (-18, '5:30 PM'),
        (18, '6:00 PM'), (-19, '6:30 PM'),
        (19, '7:00 PM'), (-20, '7:30 PM'),
        (20, '8:00 PM'), (-21, '8:30 PM'),
        (21, '9:00 PM'), (-22, '9:30 PM'),
        (22, '10:00 PM'), (-23, '10:30 PM'),
        (23, '11:00 PM'), (-24, '11:30 PM')], string='Hour to')
    # used only when the leave is taken in half days
    request_date_from_period = fields.Selection([
        ('am', 'Morning'), ('pm', 'Afternoon')],
        string="Date Period Start", default='am')
    # request type
    request_unit_half = fields.Boolean('Half Day')
    request_unit_hours = fields.Boolean('Custom Hours')
    request_unit_custom = fields.Boolean('Days-long custom hours')

    _sql_constraints = [
        ('type_value',
         "CHECK((holiday_type='employee' AND employee_id IS NOT NULL) or "
         "(holiday_type='company' AND mode_company_id IS NOT NULL) or "
         "(holiday_type='category' AND category_id IS NOT NULL) or "
         "(holiday_type='department' AND department_id IS NOT NULL) )",
         "The employee, department, company or employee category of this request is missing. Please make sure that your user login is linked to an employee."),
        ('date_check2', "CHECK ((date_from <= date_to))", "The start date must be anterior to the end date."),
        ('duration_check', "CHECK ( number_of_days >= 0 )", "If you want to change the number of days you should use the 'period' mode"),
    ]

    @api.onchange('holiday_status_id')
    def _onchange_holiday_status_id(self):
        self.request_unit_half = False
        self.request_unit_hours = False
        self.request_unit_custom = False

    @api.onchange('request_date_from_period', 'request_hour_from', 'request_hour_to',
                  'request_date_from', 'request_date_to',
                  'employee_id')
    def _onchange_request_parameters(self):
        if not self.request_date_from:
            self.date_from = False
            return

        if self.request_unit_half or self.request_unit_hours:
            self.request_date_to = self.request_date_from

        if not self.request_date_to:
            self.date_to = False
            return

        domain = [('calendar_id', '=', self.employee_id.resource_calendar_id.id or self.env.user.company_id.resource_calendar_id.id)]
        attendances = self.env['resource.calendar.attendance'].read_group(domain, ['ids:array_agg(id)', 'hour_from:min(hour_from)', 'hour_to:max(hour_to)', 'dayofweek', 'day_period'], ['dayofweek', 'day_period'], lazy=False)

        # Must be sorted by dayofweek ASC and day_period DESC
        attendances = sorted([DummyAttendance(group['hour_from'], group['hour_to'], group['dayofweek'], group['day_period']) for group in attendances], key=lambda att: (att.dayofweek, att.day_period != 'morning'))

        default_value = DummyAttendance(0, 0, 0, 'morning')

        # find first attendance coming after first_day
        attendance_from = next((att for att in attendances if int(att.dayofweek) >= self.request_date_from.weekday()), attendances[0] if attendances else default_value)
        # find last attendance coming before last_day
        attendance_to = next((att for att in reversed(attendances) if int(att.dayofweek) <= self.request_date_to.weekday()), attendances[-1] if attendances else default_value)

        if self.request_unit_half:
            if self.request_date_from_period == 'am':
                hour_from = float_to_time(attendance_from.hour_from)
                hour_to = float_to_time(attendance_from.hour_to)
            else:
                hour_from = float_to_time(attendance_to.hour_from)
                hour_to = float_to_time(attendance_to.hour_to)
        elif self.request_unit_hours:
            # This hack is related to the definition of the field, basically we convert
            # the negative integer into .5 floats
            hour_from = float_to_time(abs(self.request_hour_from) - 0.5 if self.request_hour_from < 0 else self.request_hour_from)
            hour_to = float_to_time(abs(self.request_hour_to) - 0.5 if self.request_hour_to < 0 else self.request_hour_to)
        elif self.request_unit_custom:
            hour_from = self.date_from.time()
            hour_to = self.date_to.time()
        else:
            hour_from = float_to_time(attendance_from.hour_from)
            hour_to = float_to_time(attendance_to.hour_to)
        self.date_from = timezone(self.tz).localize(datetime.combine(self.request_date_from, hour_from)).astimezone(UTC).replace(tzinfo=None)
        self.date_to = timezone(self.tz).localize(datetime.combine(self.request_date_to, hour_to)).astimezone(UTC).replace(tzinfo=None)
        self._onchange_leave_dates()

    @api.onchange('request_unit_half')
    def _onchange_request_unit_half(self):
        if self.request_unit_half:
            self.request_unit_hours = False
            self.request_unit_custom = False
        self._onchange_request_parameters()

    @api.onchange('request_unit_hours')
    def _onchange_request_unit_hours(self):
        if self.request_unit_hours:
            self.request_unit_half = False
            self.request_unit_custom = False
        self._onchange_request_parameters()

    @api.onchange('request_unit_custom')
    def _onchange_request_unit_custom(self):
        if self.request_unit_custom:
            self.request_unit_half = False
            self.request_unit_hours = False
        self._onchange_request_parameters()

    @api.onchange('holiday_type')
    def _onchange_type(self):
        if self.holiday_type == 'employee':
            if not self.employee_id:
                self.employee_id = self.env.user.employee_ids[:1].id
            self.mode_company_id = False
            self.category_id = False
        elif self.holiday_type == 'company':
            self.employee_id = False
            if not self.mode_company_id:
                self.mode_company_id = self.env.user.company_id.id
            self.category_id = False
        elif self.holiday_type == 'department':
            self.employee_id = False
            self.mode_company_id = False
            self.category_id = False
            if not self.department_id:
                self.department_id = self.env.user.employee_ids[:1].department_id.id
        elif self.holiday_type == 'category':
            self.employee_id = False
            self.mode_company_id = False
            self.department_id = False

    @api.multi
    def _sync_employee_details(self):
        for holiday in self:
            holiday.manager_id = holiday.employee_id.parent_id.id
            if holiday.employee_id:
                holiday.department_id = holiday.employee_id.department_id

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        self._sync_employee_details()
        self.holiday_status_id = False

    @api.onchange('date_from', 'date_to', 'employee_id')
    def _onchange_leave_dates(self):
        if self.date_from and self.date_to:
            self.number_of_days = self._get_number_of_days(self.date_from, self.date_to, self.employee_id.id)
        else:
            self.number_of_days = 0

    @api.depends('tz')
    def _compute_tz_mismatch(self):
        for leave in self:
            leave.tz_mismatch = leave.tz != self.env.user.tz

    @api.depends('request_unit_custom', 'employee_id', 'holiday_type', 'department_id.company_id.resource_calendar_id.tz', 'mode_company_id.resource_calendar_id.tz')
    def _compute_tz(self):
        for leave in self:
            tz = None
            if leave.request_unit_custom:
                tz = 'UTC'  # custom -> already in UTC
            elif leave.holiday_type == 'employee':
                tz = leave.employee_id.tz
            elif leave.holiday_type == 'department':
                tz = leave.department_id.company_id.resource_calendar_id.tz
            elif leave.holiday_type == 'company':
                tz = leave.mode_company_id.resource_calendar_id.tz
            tz = tz or self.env.user.company_id.resource_calendar_id.tz or self.env.user.tz or 'UTC'
            leave.tz = tz

    @api.multi
    @api.depends('number_of_days')
    def _compute_number_of_days_display(self):
        for holiday in self:
            holiday.number_of_days_display = holiday.number_of_days

    @api.multi
    @api.depends('number_of_days')
    def _compute_number_of_hours_display(self):
        for holiday in self:
            calendar = holiday.employee_id.resource_calendar_id or self.env.user.company_id.resource_calendar_id
            if holiday.date_from and holiday.date_to:
                number_of_hours = calendar.get_work_hours_count(holiday.date_from, holiday.date_to)
                holiday.number_of_hours_display = number_of_hours or (holiday.number_of_days * HOURS_PER_DAY)
            else:
                holiday.number_of_hours_display = 0

    @api.multi
    @api.depends('number_of_hours_display', 'number_of_days_display')
    def _compute_duration_display(self):
        for leave in self:
            leave.duration_display = '%g %s' % (
                (float_round(leave.number_of_hours_display, precision_digits=2)
                if leave.leave_type_request_unit == 'hour'
                else float_round(leave.number_of_days_display, precision_digits=2)),
                _('hour(s)') if leave.leave_type_request_unit == 'hour' else _('day(s)'))

    @api.multi
    @api.depends('state', 'employee_id', 'department_id')
    def _compute_can_reset(self):
        for holiday in self:
            try:
                holiday._check_approval_update('draft')
            except (AccessError, UserError):
                holiday.can_reset = False
            else:
                holiday.can_reset = True

    @api.depends('state', 'employee_id', 'department_id')
    def _compute_can_approve(self):
        for holiday in self:
            try:
                if holiday.state == 'confirm' and holiday.holiday_status_id.validation_type == 'both':
                    holiday._check_approval_update('validate1')
                else:
                    holiday._check_approval_update('validate')
            except (AccessError, UserError):
                holiday.can_approve = False
            else:
                holiday.can_approve = True

    @api.constrains('date_from', 'date_to')
    def _check_date(self):
        for holiday in self:
            domain = [
                ('date_from', '<', holiday.date_to),
                ('date_to', '>', holiday.date_from),
                ('employee_id', '=', holiday.employee_id.id),
                ('id', '!=', holiday.id),
                ('state', 'not in', ['cancel', 'refuse']),
            ]
            nholidays = self.search_count(domain)
            if nholidays:
                raise ValidationError(_('You can not have 2 leaves that overlaps on the same day.'))

    @api.constrains('state', 'number_of_days', 'holiday_status_id')
    def _check_holidays(self):
        for holiday in self:
            if holiday.holiday_type != 'employee' or not holiday.employee_id or holiday.holiday_status_id.allocation_type == 'no':
                continue
            leave_days = holiday.holiday_status_id.get_days(holiday.employee_id.id)[holiday.holiday_status_id.id]
            if float_compare(leave_days['remaining_leaves'], 0, precision_digits=2) == -1 or \
              float_compare(leave_days['virtual_remaining_leaves'], 0, precision_digits=2) == -1:
                raise ValidationError(_('The number of remaining leaves is not sufficient for this leave type.\n'
                                        'Please also check the leaves waiting for validation.'))

    def _get_number_of_days(self, date_from, date_to, employee_id):
        """ Returns a float equals to the timedelta between two dates given as string."""
        if employee_id:
            employee = self.env['hr.employee'].browse(employee_id)
            return employee.get_work_days_data(date_from, date_to)['days']

        today_hours = self.env.user.company_id.resource_calendar_id.get_work_hours_count(
            datetime.combine(date_from.date(), time.min),
            datetime.combine(date_from.date(), time.max),
            False)

        return self.env.user.company_id.resource_calendar_id.get_work_hours_count(date_from, date_to) / (today_hours or HOURS_PER_DAY)

    ####################################################
    # ORM Overrides methods
    ####################################################

    @api.multi
    def name_get(self):
        res = []
        for leave in self:
            if self.env.context.get('short_name'):
                if leave.leave_type_request_unit == 'hour':
                    res.append((leave.id, _("%s : %.2f hour(s)") % (leave.name or leave.holiday_status_id.name, leave.number_of_hours_display)))
                else:
                    res.append((leave.id, _("%s : %.2f day(s)") % (leave.name or leave.holiday_status_id.name, leave.number_of_days)))
            else:
                if leave.holiday_type == 'company':
                    target = leave.mode_company_id.name
                elif leave.holiday_type == 'department':
                    target = leave.department_id.name
                elif leave.holiday_type == 'category':
                    target = leave.category_id.name
                else:
                    target = leave.employee_id.name
                if leave.leave_type_request_unit == 'hour':
                    res.append(
                        (leave.id,
                        _("%s on %s : %.2f hour(s)") %
                        (target, leave.holiday_status_id.name, leave.number_of_hours_display))
                    )
                else:
                    res.append(
                        (leave.id,
                        _("%s on %s : %.2f day(s)") %
                        (target, leave.holiday_status_id.name, leave.number_of_days))
                    )
        return res

    @api.multi
    def add_follower(self, employee_id):
        employee = self.env['hr.employee'].browse(employee_id)
        if employee.user_id:
            self.message_subscribe(partner_ids=employee.user_id.partner_id.ids)

    @api.multi
    @api.constrains('holiday_status_id', 'date_to', 'date_from')
    def _check_leave_type_validity(self):
        for leave in self:
            vstart = leave.holiday_status_id.validity_start
            vstop  = leave.holiday_status_id.validity_stop
            dfrom  = leave.date_from
            dto    = leave.date_to
            if leave.holiday_status_id.validity_start and leave.holiday_status_id.validity_stop:
                if dfrom and dto and (dfrom.date() < vstart or dto.date() > vstop):
                    raise UserError(
                        _('You can take %s only between %s and %s') % (
                            leave.holiday_status_id.display_name, leave.holiday_status_id.validity_start, leave.holiday_status_id.validity_stop))
            elif leave.holiday_status_id.validity_start:
                if dfrom and (dfrom.date() < vstart):
                    raise UserError(
                        _('You can take %s from %s') % (
                            leave.holiday_status_id.display_name, leave.holiday_status_id.validity_start))
            elif leave.holiday_status_id.validity_stop:
                if dto and (dto.date() > vstop):
                    raise UserError(
                        _('You can take %s until %s') % (
                            leave.holiday_status_id.display_name, leave.holiday_status_id.validity_stop))

    @api.model
    def create(self, values):
        """ Override to avoid automatic logging of creation """
        employee_id = values.get('employee_id', False)
        if not values.get('department_id'):
            values.update({'department_id': self.env['hr.employee'].browse(employee_id).department_id.id})
        holiday = super(HolidaysRequest, self.with_context(mail_create_nolog=True, mail_create_nosubscribe=True)).create(values)
        if self._context.get('import_file'):
            holiday._onchange_leave_dates()
        if not self._context.get('leave_fast_create'):
            holiday.add_follower(employee_id)
            if 'employee_id' in values:
                holiday._sync_employee_details()
            if not self._context.get('import_file'):
                holiday.activity_update()
        return holiday

    def _read_from_database(self, field_names, inherited_field_names=[]):
        if 'name' in field_names and 'employee_id' not in field_names:
            field_names.append('employee_id')
        super(HolidaysRequest, self)._read_from_database(field_names, inherited_field_names)
        if 'name' in field_names:
            if self.user_has_groups('hr_holidays.group_hr_holidays_user'):
                return
            current_employee = self.env['hr.employee'].sudo().search([('user_id', '=', self.env.uid)], limit=1)
            for record in self:
                emp_id = record._cache.get('employee_id', False) and record._cache.get('employee_id')[0]
                if emp_id != current_employee.id:
                    try:
                        record._cache['name']
                        record._cache['name'] = '*****'
                    except Exception:
                        # skip SpecialValue (e.g. for missing record or access right)
                        pass

    @api.multi
    def write(self, values):
        employee_id = values.get('employee_id', False)
        if not self.env.context.get('leave_fast_create') and values.get('state'):
            self._check_approval_update(values['state'])
        result = super(HolidaysRequest, self).write(values)
        if not self.env.context.get('leave_fast_create'):
            self.add_follower(employee_id)
            if 'employee_id' in values:
                self._sync_employee_details()
        return result

    @api.multi
    def unlink(self):
        for holiday in self.filtered(lambda holiday: holiday.state not in ['draft', 'cancel', 'confirm']):
            raise UserError(_('You cannot delete a leave which is in %s state.') % (holiday.state,))
        return super(HolidaysRequest, self).unlink()

    @api.multi
    def copy_data(self, default=None):
        raise UserError(_('A leave cannot be duplicated.'))

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        if not self.user_has_groups('hr_holidays.group_hr_holidays_user') and 'name' in groupby:
            raise UserError(_('Such grouping is not allowed.'))
        return super(HolidaysRequest, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)

    ####################################################
    # Business methods
    ####################################################

    @api.multi
    def _create_resource_leave(self):
        """ This method will create entry in resource calendar leave object at the time of holidays validated """
        for leave in self:
            date_from = fields.Datetime.from_string(leave.date_from)
            date_to = fields.Datetime.from_string(leave.date_to)

            self.env['resource.calendar.leaves'].create({
                'name': leave.name,
                'date_from': fields.Datetime.to_string(date_from),
                'holiday_id': leave.id,
                'date_to': fields.Datetime.to_string(date_to),
                'resource_id': leave.employee_id.resource_id.id,
                'calendar_id': leave.employee_id.resource_calendar_id.id,
                'time_type': leave.holiday_status_id.time_type,
            })
        return True

    @api.multi
    def _remove_resource_leave(self):
        """ This method will create entry in resource calendar leave object at the time of holidays cancel/removed """
        return self.env['resource.calendar.leaves'].search([('holiday_id', 'in', self.ids)]).unlink()

    def _validate_leave_request(self):
        """ Validate leave requests (holiday_type='employee')
        by creating a calendar event and a resource leaves. """
        holidays = self.filtered(lambda request: request.holiday_type == 'employee')
        holidays._create_resource_leave()
        for holiday in holidays:
            meeting_values = holiday._prepare_holidays_meeting_values()
            meeting = self.env['calendar.event'].with_context(no_mail_to_attendees=True).create(meeting_values)
            holiday.write({'meeting_id': meeting.id})

    @api.multi
    def _prepare_holidays_meeting_values(self):
        self.ensure_one()
        calendar = self.employee_id.resource_calendar_id or self.env.user.company_id.resource_calendar_id
        if self.leave_type_request_unit == 'hour':
            meeting_name = _("%s on Time Off : %.2f hour(s)") % (self.employee_id.name or self.category_id.name, self.number_of_hours_display)
        else:
            meeting_name = _("%s on Time Off : %.2f day(s)") % (self.employee_id.name or self.category_id.name, self.number_of_days)

        meeting_values = {
            'name': meeting_name,
            'categ_ids': [(6, 0, [
                self.holiday_status_id.categ_id.id])] if self.holiday_status_id.categ_id else [],
            'duration': self.number_of_days * (calendar.hours_per_day or HOURS_PER_DAY),
            'description': self.notes,
            'user_id': self.user_id.id,
            'start': self.date_from,
            'stop': self.date_to,
            'allday': False,
            'state': 'open',  # to block that meeting date in the calendar
            'privacy': 'confidential'
        }
        # Add the partner_id (if exist) as an attendee
        if self.user_id and self.user_id.partner_id:
            meeting_values['partner_ids'] = [
                (4, self.user_id.partner_id.id)]
        return meeting_values

    @api.multi
    def _prepare_holiday_values(self, employee):
        self.ensure_one()
        values = {
            'name': self.name,
            'holiday_type': 'employee',
            'holiday_status_id': self.holiday_status_id.id,
            'date_from': self.date_from,
            'date_to': self.date_to,
            'request_date_from': self.date_from,
            'request_date_to': self.date_to,
            'notes': self.notes,
            'number_of_days': employee.get_work_days_data(self.date_from, self.date_to)['days'],
            'parent_id': self.id,
            'employee_id': employee.id
        }
        return values

    @api.multi
    def action_draft(self):
        if any(holiday.state not in ['confirm', 'refuse'] for holiday in self):
            raise UserError(_('Leave request state must be "Refused" or "To Approve" in order to be reset to draft.'))
        self.write({
            'state': 'draft',
            'first_approver_id': False,
            'second_approver_id': False,
        })
        linked_requests = self.mapped('linked_request_ids')
        if linked_requests:
            linked_requests.action_draft()
            linked_requests.unlink()
        self.activity_update()
        return True

    @api.multi
    def action_confirm(self):
        if self.filtered(lambda holiday: holiday.state != 'draft'):
            raise UserError(_('Leave request must be in Draft state ("To Submit") in order to confirm it.'))
        self.write({'state': 'confirm'})
        self.activity_update()
        return True

    @api.multi
    def action_approve(self):
        # if validation_type == 'both': this method is the first approval approval
        # if validation_type != 'both': this method calls action_validate() below
        if any(holiday.state != 'confirm' for holiday in self):
            raise UserError(_('Leave request must be confirmed ("To Approve") in order to approve it.'))

        current_employee = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
        self.filtered(lambda hol: hol.validation_type == 'both').write({'state': 'validate1', 'first_approver_id': current_employee.id})
        self.filtered(lambda hol: not hol.validation_type == 'both').action_validate()
        if not self.env.context.get('leave_fast_create'):
            self.activity_update()
        return True

    @api.multi
    def action_validate(self):
        current_employee = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
        if any(holiday.state not in ['confirm', 'validate1'] for holiday in self):
            raise UserError(_('Leave request must be confirmed in order to approve it.'))

        self.write({'state': 'validate'})
        self.filtered(lambda holiday: holiday.validation_type == 'both').write({'second_approver_id': current_employee.id})
        self.filtered(lambda holiday: holiday.validation_type != 'both').write({'first_approver_id': current_employee.id})

        for holiday in self.filtered(lambda holiday: holiday.holiday_type != 'employee'):
            if holiday.holiday_type == 'category':
                employees = holiday.category_id.employee_ids
            elif holiday.holiday_type == 'company':
                employees = self.env['hr.employee'].search([('company_id', '=', holiday.mode_company_id.id)])
            else:
                employees = holiday.department_id.member_ids

            if self.env['hr.leave'].search_count([('date_from', '<=', holiday.date_to), ('date_to', '>', holiday.date_from),
                               ('state', 'not in', ['cancel', 'refuse']), ('holiday_type', '=', 'employee'),
                               ('employee_id', 'in', employees.ids)]):
                raise ValidationError(_('You can not have 2 leaves that overlaps on the same day.'))

            values = [holiday._prepare_holiday_values(employee) for employee in employees]
            leaves = self.env['hr.leave'].with_context(
                tracking_disable=True,
                mail_activity_automation_skip=True,
                leave_fast_create=True,
            ).create(values)
            leaves.action_approve()
            # FIXME RLi: This does not make sense, only the parent should be in validation_type both
            if leaves and leaves[0].validation_type == 'both':
                leaves.action_validate()

        employee_requests = self.filtered(lambda hol: hol.holiday_type == 'employee')
        employee_requests._validate_leave_request()
        if not self.env.context.get('leave_fast_create'):
            employee_requests.activity_update()
        return True

    @api.multi
    def action_refuse(self):
        current_employee = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
        if any(holiday.state not in ['confirm', 'validate', 'validate1'] for holiday in self):
            raise UserError(_('Leave request must be confirmed or validated in order to refuse it.'))

        validated_holidays = self.filtered(lambda hol: hol.state == 'validate1')
        validated_holidays.write({'state': 'refuse', 'first_approver_id': current_employee.id})
        (self - validated_holidays).write({'state': 'refuse', 'second_approver_id': current_employee.id})
        # Delete the meeting
        self.mapped('meeting_id').unlink()
        # If a category that created several holidays, cancel all related
        linked_requests = self.mapped('linked_request_ids')
        if linked_requests:
            linked_requests.action_refuse()
        self._remove_resource_leave()
        self.activity_update()
        return True

    def _check_approval_update(self, state):
        """ Check if target state is achievable. """
        current_employee = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
        is_officer = self.env.user.has_group('hr_holidays.group_hr_holidays_user')
        is_manager = self.env.user.has_group('hr_holidays.group_hr_holidays_manager')
        for holiday in self:
            val_type = holiday.holiday_status_id.validation_type
            if state == 'confirm':
                continue

            if state == 'draft':
                if holiday.employee_id != current_employee and not is_manager:
                    raise UserError(_('Only a Leave Manager can reset other people leaves.'))
                continue

            if not is_officer:
                raise UserError(_('Only a Leave Officer or Manager can approve or refuse leave requests.'))

            if is_officer:
                # use ir.rule based first access check: department, members, ... (see security.xml)
                holiday.check_access_rule('write')

            if holiday.employee_id == current_employee and not is_manager:
                raise UserError(_('Only a Leave Manager can approve its own requests.'))

            if (state == 'validate1' and val_type == 'both') or (state == 'validate' and val_type == 'manager'):
                manager = holiday.employee_id.parent_id or holiday.employee_id.department_id.manager_id
                if (manager and manager != current_employee) and not self.env.user.has_group('hr_holidays.group_hr_holidays_manager'):
                    raise UserError(_('You must be either %s\'s manager or Leave manager to approve this leave') % (holiday.employee_id.name))

            if state == 'validate' and val_type == 'both':
                if not self.env.user.has_group('hr_holidays.group_hr_holidays_manager'):
                    raise UserError(_('Only an Leave Manager can apply the second approval on leave requests.'))

    # ------------------------------------------------------------
    # Activity methods
    # ------------------------------------------------------------

    def _get_responsible_for_approval(self):
        if self.state == 'confirm' and self.manager_id.user_id:
            return self.manager_id.user_id
        elif self.state == 'confirm' and self.employee_id.parent_id.user_id:
            return self.employee_id.parent_id.user_id
        elif self.department_id.manager_id.user_id:
            return self.department_id.manager_id.user_id
        return self.env['res.users']

    def activity_update(self):
        to_clean, to_do = self.env['hr.leave'], self.env['hr.leave']
        for holiday in self:
            start = UTC.localize(holiday.date_from).astimezone(timezone(holiday.employee_id.tz or 'UTC'))
            end = UTC.localize(holiday.date_to).astimezone(timezone(holiday.employee_id.tz or 'UTC'))
            note = _('New %s Request created by %s from %s to %s') % (holiday.holiday_status_id.name, holiday.create_uid.name, start, end)
            if holiday.state == 'draft':
                to_clean |= holiday
            elif holiday.state == 'confirm':
                holiday.activity_schedule(
                    'hr_holidays.mail_act_leave_approval',
                    note=note,
                    user_id=holiday.sudo()._get_responsible_for_approval().id or self.env.user.id)
            elif holiday.state == 'validate1':
                holiday.activity_feedback(['hr_holidays.mail_act_leave_approval'])
                holiday.activity_schedule(
                    'hr_holidays.mail_act_leave_second_approval',
                    note=note,
                    user_id=holiday.sudo()._get_responsible_for_approval().id or self.env.user.id)
            elif holiday.state == 'validate':
                to_do |= holiday
            elif holiday.state == 'refuse':
                to_clean |= holiday
        if to_clean:
            to_clean.activity_unlink(['hr_holidays.mail_act_leave_approval', 'hr_holidays.mail_act_leave_second_approval'])
        if to_do:
            to_do.activity_feedback(['hr_holidays.mail_act_leave_approval', 'hr_holidays.mail_act_leave_second_approval'])

    ####################################################
    # Messaging methods
    ####################################################

    @api.multi
    def _track_subtype(self, init_values):
        if 'state' in init_values and self.state == 'validate':
            return 'hr_holidays.mt_leave_approved'
        elif 'state' in init_values and self.state == 'refuse':
            return 'hr_holidays.mt_leave_refused'
        return super(HolidaysRequest, self)._track_subtype(init_values)

    @api.multi
    def _notify_get_groups(self, message, groups):
        """ Handle HR users and officers recipients that can validate or refuse holidays
        directly from email. """
        groups = super(HolidaysRequest, self)._notify_get_groups(message, groups)

        self.ensure_one()
        hr_actions = []
        if self.state == 'confirm':
            app_action = self._notify_get_action_link('controller', controller='/leave/validate')
            hr_actions += [{'url': app_action, 'title': _('Approve')}]
        if self.state in ['confirm', 'validate', 'validate1']:
            ref_action = self._notify_get_action_link('controller', controller='/leave/refuse')
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
            return super(HolidaysRequest, self.sudo()).message_subscribe(partner_ids=partner_ids, channel_ids=channel_ids, subtype_ids=subtype_ids)
        return super(HolidaysRequest, self).message_subscribe(partner_ids=partner_ids, channel_ids=channel_ids, subtype_ids=subtype_ids)
