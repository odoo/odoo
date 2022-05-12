# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (c) 2005-2006 Axelor SARL. (http://www.axelor.com)

import logging
import pytz

from collections import namedtuple, defaultdict

from datetime import datetime, timedelta, time
from pytz import timezone, UTC
from odoo.tools import date_utils

from odoo import api, Command, fields, models, tools, SUPERUSER_ID
from odoo.addons.base.models.res_partner import _tz_get
from odoo.addons.resource.models.resource import float_to_time, HOURS_PER_DAY
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools import float_compare
from odoo.tools.float_utils import float_round
from odoo.tools.misc import format_date
from odoo.tools.translate import _
from odoo.osv import expression

_logger = logging.getLogger(__name__)

# Used to agglomerate the attendances in order to find the hour_from and hour_to
# See _compute_date_from_to
DummyAttendance = namedtuple('DummyAttendance', 'hour_from, hour_to, dayofweek, day_period, week_type')

def get_employee_from_context(values, context, user_employee_id):
    employee_ids_list = [value[2] for value in values.get('employee_ids', []) if len(value) == 3 and value[0] == Command.SET]
    employee_ids = employee_ids_list[-1] if employee_ids_list else []
    employee_id_value = employee_ids[0] if employee_ids else False
    return employee_id_value or context.get('default_employee_id', context.get('employee_id', user_employee_id))

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
    _description = "Time Off"
    _order = "date_from desc"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _mail_post_access = 'read'

    @api.model
    def default_get(self, fields_list):
        defaults = super(HolidaysRequest, self).default_get(fields_list)
        defaults = self._default_get_request_parameters(defaults)

        if 'holiday_status_id' in fields_list and not defaults.get('holiday_status_id'):
            lt = self.env['hr.leave.type'].search(['|', ('requires_allocation', '=', 'no'), ('has_valid_allocation', '=', True)], limit=1, order='sequence')

            if lt:
                defaults['holiday_status_id'] = lt.id
                defaults['request_unit_custom'] = False

        if 'state' in fields_list and not defaults.get('state'):
            lt = self.env['hr.leave.type'].browse(defaults.get('holiday_status_id'))
            defaults['state'] = 'confirm'

        if 'date_from' and 'date_to' in fields_list:
            now = fields.Datetime.now()
            if 'date_from' not in defaults:
                defaults['date_from'] = now.replace(hour=0, minute=0, second=0)
            if 'date_to' not in defaults:
                defaults['date_to'] = now.replace(hour=23, minute=59, second=59)
            if (not self._context.get('leave_compute_date_from_to') and defaults['date_from'].time() == time(0, 0, 0) and
                    defaults['date_to'].time() == time(23, 59, 59)):
                employee = self.env['hr.employee'].browse(defaults['employee_id']) if defaults.get('employee_id') else self.env.user.employee_id

                date_from = defaults['date_from'].date()
                date_to = defaults['date_to'].date()

                attendance_from, attendance_to = self._get_attendances(employee, date_from, date_to)

                defaults['date_from'] = self._get_start_or_end_from_attendance(attendance_from.hour_from, date_from, employee)
                defaults['date_to'] = self._get_start_or_end_from_attendance(attendance_to.hour_to, date_to, employee)

        defaults = self._default_get_request_parameters(defaults)

        return defaults

    def _default_get_request_parameters(self, values):
        new_values = dict(values)
        if values.get('date_from'):
            new_values['request_date_from'] = values['date_from'].date()
        if values.get('date_to'):
            new_values['request_date_to'] = values['date_to'].date()
        return new_values

    active = fields.Boolean(default=True, readonly=True)
    # description
    name = fields.Char('Description', compute='_compute_description', inverse='_inverse_description', search='_search_description', compute_sudo=False)
    private_name = fields.Char('Time Off Description', groups='hr_holidays.group_hr_holidays_user')
    state = fields.Selection([
        ('draft', 'To Submit'),
        ('confirm', 'To Approve'),
        ('refuse', 'Refused'),
        ('validate1', 'Second Approval'),
        ('validate', 'Approved')
        ], string='Status', compute='_compute_state', store=True, tracking=True, copy=False, readonly=False,
        help="The status is set to 'To Submit', when a time off request is created." +
        "\nThe status is 'To Approve', when time off request is confirmed by user." +
        "\nThe status is 'Refused', when time off request is refused by manager." +
        "\nThe status is 'Approved', when time off request is approved by manager.")
    report_note = fields.Text('HR Comments', copy=False, groups="hr_holidays.group_hr_holidays_manager")
    user_id = fields.Many2one('res.users', string='User', related='employee_id.user_id', related_sudo=True, compute_sudo=True, store=True, readonly=True, index=True)
    manager_id = fields.Many2one('hr.employee', compute='_compute_from_employee_id', store=True, readonly=False)
    # leave type configuration
    holiday_status_id = fields.Many2one(
        "hr.leave.type", compute='_compute_from_employee_id', store=True, string="Time Off Type", required=True, readonly=False,
        states={'cancel': [('readonly', True)], 'refuse': [('readonly', True)], 'validate1': [('readonly', True)], 'validate': [('readonly', True)]},
        domain=['|', ('requires_allocation', '=', 'no'), ('has_valid_allocation', '=', True)])
    holiday_allocation_id = fields.Many2one(
        'hr.leave.allocation', compute='_compute_from_holiday_status_id', string="Allocation", store=True, readonly=False)
    color = fields.Integer("Color", related='holiday_status_id.color')
    validation_type = fields.Selection(string='Validation Type', related='holiday_status_id.leave_validation_type', readonly=False)
    # HR data

    employee_id = fields.Many2one(
        'hr.employee', compute='_compute_from_employee_ids', store=True, string='Employee', index=True, readonly=False, ondelete="restrict",
        states={'cancel': [('readonly', True)], 'refuse': [('readonly', True)], 'validate1': [('readonly', True)], 'validate': [('readonly', True)]},
        tracking=True)
    employee_company_id = fields.Many2one(related='employee_id.company_id', readonly=True, store=True)
    active_employee = fields.Boolean(related='employee_id.active', string='Employee Active', readonly=True)
    tz_mismatch = fields.Boolean(compute='_compute_tz_mismatch')
    tz = fields.Selection(_tz_get, compute='_compute_tz')
    department_id = fields.Many2one(
        'hr.department', compute='_compute_department_id', store=True, string='Department', readonly=False,
        states={'cancel': [('readonly', True)], 'refuse': [('readonly', True)], 'validate1': [('readonly', True)], 'validate': [('readonly', True)]})
    notes = fields.Text('Reasons', readonly=True, states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    # duration
    date_from = fields.Datetime(
        'Start Date', compute='_compute_date_from_to', store=True, readonly=False, index=True, copy=False, required=True, tracking=True,
        states={'cancel': [('readonly', True)], 'refuse': [('readonly', True)], 'validate1': [('readonly', True)], 'validate': [('readonly', True)]})
    date_to = fields.Datetime(
        'End Date', compute='_compute_date_from_to', store=True, readonly=False, copy=False, required=True, tracking=True,
        states={'cancel': [('readonly', True)], 'refuse': [('readonly', True)], 'validate1': [('readonly', True)], 'validate': [('readonly', True)]})
    number_of_days = fields.Float(
        'Duration (Days)', compute='_compute_number_of_days', store=True, readonly=False, copy=False, tracking=True,
        help='Number of days of the time off request. Used in the calculation. To manually correct the duration, use this field.')
    number_of_days_display = fields.Float(
        'Duration in days', compute='_compute_number_of_days_display', readonly=True,
        help='Number of days of the time off request according to your working schedule. Used for interface.')
    number_of_hours_display = fields.Float(
        'Duration in hours', compute='_compute_number_of_hours_display', readonly=True,
        help='Number of hours of the time off request according to your working schedule. Used for interface.')
    number_of_hours_text = fields.Char(compute='_compute_number_of_hours_text')
    duration_display = fields.Char('Requested (Days/Hours)', compute='_compute_duration_display', store=True,
        help="Field allowing to see the leave request duration in days or hours depending on the leave_type_request_unit")    # details
    # details
    meeting_id = fields.Many2one('calendar.event', string='Meeting', copy=False)
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
    employee_ids = fields.Many2many(
        'hr.employee', compute='_compute_from_holiday_type', store=True, string='Employees', readonly=False,
        states={'cancel': [('readonly', True)], 'refuse': [('readonly', True)], 'validate1': [('readonly', True)], 'validate': [('readonly', True)]})
    multi_employee = fields.Boolean(
        compute='_compute_from_employee_ids', store=True,
        help='Holds whether this allocation concerns more than 1 employee')
    category_id = fields.Many2one(
        'hr.employee.category', compute='_compute_from_holiday_type', store=True, string='Employee Tag',
        states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]}, help='Category of Employee')
    mode_company_id = fields.Many2one(
        'res.company', compute='_compute_from_holiday_type', store=True, string='Company Mode',
        states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    first_approver_id = fields.Many2one(
        'hr.employee', string='First Approval', readonly=True, copy=False,
        help='This area is automatically filled by the user who validate the time off')
    second_approver_id = fields.Many2one(
        'hr.employee', string='Second Approval', readonly=True, copy=False,
        help='This area is automatically filled by the user who validate the time off with second level (If time off type need second validation)')
    can_reset = fields.Boolean('Can reset', compute='_compute_can_reset')
    can_approve = fields.Boolean('Can Approve', compute='_compute_can_approve')
    can_cancel = fields.Boolean('Can Cancel', compute='_compute_can_cancel')

    attachment_ids = fields.One2many('ir.attachment', 'res_id', string="Attachments")
    # To display in form view
    supported_attachment_ids = fields.Many2many(
        'ir.attachment', string="Attach File", compute='_compute_supported_attachment_ids',
        inverse='_inverse_supported_attachment_ids')
    supported_attachment_ids_count = fields.Integer(compute='_compute_supported_attachment_ids')
    # UX fields
    all_employee_ids = fields.Many2many('hr.employee', compute='_compute_all_employees')
    leave_type_request_unit = fields.Selection(related='holiday_status_id.request_unit', readonly=True)
    leave_type_support_document = fields.Boolean(related="holiday_status_id.support_document")
    # Interface fields used when not using hour-based computation
    request_date_from = fields.Date('Request Start Date')
    request_date_to = fields.Date('Request End Date')
    # Interface fields used when using hour-based computation
    request_hour_from = fields.Selection([
        ('0', '12:00 AM'), ('0.5', '12:30 AM'),
        ('1', '1:00 AM'), ('1.5', '1:30 AM'),
        ('2', '2:00 AM'), ('2.5', '2:30 AM'),
        ('3', '3:00 AM'), ('3.5', '3:30 AM'),
        ('4', '4:00 AM'), ('4.5', '4:30 AM'),
        ('5', '5:00 AM'), ('5.5', '5:30 AM'),
        ('6', '6:00 AM'), ('6.5', '6:30 AM'),
        ('7', '7:00 AM'), ('7.5', '7:30 AM'),
        ('8', '8:00 AM'), ('8.5', '8:30 AM'),
        ('9', '9:00 AM'), ('9.5', '9:30 AM'),
        ('10', '10:00 AM'), ('10.5', '10:30 AM'),
        ('11', '11:00 AM'), ('11.5', '11:30 AM'),
        ('12', '12:00 PM'), ('12.5', '12:30 PM'),
        ('13', '1:00 PM'), ('13.5', '1:30 PM'),
        ('14', '2:00 PM'), ('14.5', '2:30 PM'),
        ('15', '3:00 PM'), ('15.5', '3:30 PM'),
        ('16', '4:00 PM'), ('16.5', '4:30 PM'),
        ('17', '5:00 PM'), ('17.5', '5:30 PM'),
        ('18', '6:00 PM'), ('18.5', '6:30 PM'),
        ('19', '7:00 PM'), ('19.5', '7:30 PM'),
        ('20', '8:00 PM'), ('20.5', '8:30 PM'),
        ('21', '9:00 PM'), ('21.5', '9:30 PM'),
        ('22', '10:00 PM'), ('22.5', '10:30 PM'),
        ('23', '11:00 PM'), ('23.5', '11:30 PM')], string='Hour from')
    request_hour_to = fields.Selection([
        ('0', '12:00 AM'), ('0.5', '12:30 AM'),
        ('1', '1:00 AM'), ('1.5', '1:30 AM'),
        ('2', '2:00 AM'), ('2.5', '2:30 AM'),
        ('3', '3:00 AM'), ('3.5', '3:30 AM'),
        ('4', '4:00 AM'), ('4.5', '4:30 AM'),
        ('5', '5:00 AM'), ('5.5', '5:30 AM'),
        ('6', '6:00 AM'), ('6.5', '6:30 AM'),
        ('7', '7:00 AM'), ('7.5', '7:30 AM'),
        ('8', '8:00 AM'), ('8.5', '8:30 AM'),
        ('9', '9:00 AM'), ('9.5', '9:30 AM'),
        ('10', '10:00 AM'), ('10.5', '10:30 AM'),
        ('11', '11:00 AM'), ('11.5', '11:30 AM'),
        ('12', '12:00 PM'), ('12.5', '12:30 PM'),
        ('13', '1:00 PM'), ('13.5', '1:30 PM'),
        ('14', '2:00 PM'), ('14.5', '2:30 PM'),
        ('15', '3:00 PM'), ('15.5', '3:30 PM'),
        ('16', '4:00 PM'), ('16.5', '4:30 PM'),
        ('17', '5:00 PM'), ('17.5', '5:30 PM'),
        ('18', '6:00 PM'), ('18.5', '6:30 PM'),
        ('19', '7:00 PM'), ('19.5', '7:30 PM'),
        ('20', '8:00 PM'), ('20.5', '8:30 PM'),
        ('21', '9:00 PM'), ('21.5', '9:30 PM'),
        ('22', '10:00 PM'), ('22.5', '10:30 PM'),
        ('23', '11:00 PM'), ('23.5', '11:30 PM')], string='Hour to')
    # used only when the leave is taken in half days
    request_date_from_period = fields.Selection([
        ('am', 'Morning'), ('pm', 'Afternoon')],
        string="Date Period Start", default='am')
    # request type
    request_unit_half = fields.Boolean('Half Day', compute='_compute_request_unit_half', store=True, readonly=False)
    request_unit_hours = fields.Boolean('Custom Hours', compute='_compute_request_unit_hours', store=True, readonly=False)
    # view
    is_hatched = fields.Boolean('Hatched', compute='_compute_is_hatched')
    is_striked = fields.Boolean('Striked', compute='_compute_is_hatched')
    has_stress_day = fields.Boolean(compute='_compute_has_stress_day')

    _sql_constraints = [
        ('type_value',
         "CHECK((holiday_type='employee' AND (employee_id IS NOT NULL OR multi_employee IS TRUE)) or "
         "(holiday_type='company' AND mode_company_id IS NOT NULL) or "
         "(holiday_type='category' AND category_id IS NOT NULL) or "
         "(holiday_type='department' AND department_id IS NOT NULL) )",
         "The employee, department, company or employee category of this request is missing. Please make sure that your user login is linked to an employee."),
        ('date_check2', "CHECK ((date_from <= date_to))", "The start date must be anterior to the end date."),
        ('duration_check', "CHECK ( number_of_days >= 0 )", "If you want to change the number of days you should use the 'period' mode"),
    ]

    def _auto_init(self):
        res = super(HolidaysRequest, self)._auto_init()
        tools.create_index(self._cr, 'hr_leave_date_to_date_from_index',
                           self._table, ['date_to', 'date_from'])
        return res

    @api.depends('employee_id', 'employee_ids')
    def _compute_all_employees(self):
        for leave in self:
            leave.all_employee_ids = leave.employee_id | leave.employee_ids

    @api.constrains('holiday_status_id', 'number_of_days')
    def _check_allocation_duration(self):
        # Deprecated as part of https://github.com/odoo/odoo/pull/96545
        # TODO: remove in master
        return

    @api.depends_context('uid')
    def _compute_description(self):
        self.check_access_rights('read')
        self.check_access_rule('read')

        is_officer = self.user_has_groups('hr_holidays.group_hr_holidays_user')

        for leave in self:
            if is_officer or leave.user_id == self.env.user or leave.employee_id.leave_manager_id == self.env.user:
                leave.name = leave.sudo().private_name
            else:
                leave.name = '*****'

    def _inverse_description(self):
        is_officer = self.user_has_groups('hr_holidays.group_hr_holidays_user')

        for leave in self:
            if is_officer or leave.user_id == self.env.user or leave.employee_id.leave_manager_id == self.env.user:
                leave.sudo().private_name = leave.name

    def _search_description(self, operator, value):
        is_officer = self.user_has_groups('hr_holidays.group_hr_holidays_user')
        domain = [('private_name', operator, value)]

        if not is_officer:
            domain = expression.AND([domain, [('user_id', '=', self.env.user.id)]])

        leaves = self.search(domain)
        return [('id', 'in', leaves.ids)]

    @api.depends('holiday_status_id')
    def _compute_state(self):
        for leave in self:
            leave.state = 'confirm' if leave.validation_type != 'no_validation' else 'draft'

    @api.depends('holiday_status_id.requires_allocation', 'validation_type', 'employee_id', 'date_from', 'date_to')
    def _compute_from_holiday_status_id(self):
        # Deprecated as part of https://github.com/odoo/odoo/pull/96545
        # TODO: remove in master
        self.holiday_allocation_id = False

    @api.depends('request_date_from_period', 'request_hour_from', 'request_hour_to', 'request_date_from', 'request_date_to',
                 'request_unit_half', 'request_unit_hours', 'employee_id')
    def _compute_date_from_to(self):
        for holiday in self:
            if holiday.request_date_from and holiday.request_date_to and holiday.request_date_from > holiday.request_date_to:
                holiday.request_date_to = holiday.request_date_from
            if not holiday.request_date_from:
                holiday.date_from = False
            elif not holiday.request_unit_half and not holiday.request_unit_hours and not holiday.request_date_to:
                holiday.date_to = False
            else:
                if holiday.request_unit_half or holiday.request_unit_hours:
                    holiday.request_date_to = holiday.request_date_from

                attendance_from, attendance_to = holiday._get_attendances(holiday.employee_id, holiday.request_date_from, holiday.request_date_to)

                compensated_request_date_from = holiday.request_date_from
                compensated_request_date_to = holiday.request_date_to

                if holiday.request_unit_half:
                    if holiday.request_date_from_period == 'am':
                        hour_from = attendance_from.hour_from
                        hour_to = attendance_from.hour_to
                    else:
                        hour_from = attendance_to.hour_from
                        hour_to = attendance_to.hour_to
                elif holiday.request_unit_hours:
                    hour_from = holiday.request_hour_from
                    hour_to = holiday.request_hour_to
                else:
                    hour_from = attendance_from.hour_from
                    hour_to = attendance_to.hour_to

                holiday.date_from = self._get_start_or_end_from_attendance(hour_from, compensated_request_date_from, holiday.employee_id or holiday)
                holiday.date_to = self._get_start_or_end_from_attendance(hour_to, compensated_request_date_to, holiday.employee_id or holiday)

    @api.depends('holiday_status_id', 'request_unit_hours')
    def _compute_request_unit_half(self):
        for holiday in self:
            if holiday.holiday_status_id or holiday.request_unit_hours:
                holiday.request_unit_half = False

    @api.depends('holiday_status_id', 'request_unit_half')
    def _compute_request_unit_hours(self):
        for holiday in self:
            if holiday.holiday_status_id or holiday.request_unit_half:
                holiday.request_unit_hours = False

    @api.depends('employee_ids')
    def _compute_from_employee_ids(self):
        for holiday in self:
            if len(holiday.employee_ids) == 1:
                holiday.employee_id = holiday.employee_ids[0]._origin
            else:
                holiday.employee_id = False
            holiday.multi_employee = (len(holiday.employee_ids) > 1)

    @api.depends('holiday_type')
    def _compute_from_holiday_type(self):
        allocation_from_domain = self.env['hr.leave.allocation']
        if (self._context.get('active_model') == 'hr.leave.allocation' and
           self._context.get('active_id')):
            allocation_from_domain = allocation_from_domain.browse(self._context['active_id'])
        for holiday in self:
            if holiday.holiday_type == 'employee':
                if not holiday.employee_ids:
                    if allocation_from_domain:
                        holiday.employee_ids = allocation_from_domain.employee_id
                        holiday.holiday_status_id = allocation_from_domain.holiday_status_id
                    else:
                        # This handles the case where a request is made with only the employee_id
                        # but does not need to be recomputed on employee_id changes
                        holiday.employee_ids = holiday.employee_id or self.env.user.employee_id
                holiday.mode_company_id = False
                holiday.category_id = False
            elif holiday.holiday_type == 'company':
                holiday.employee_ids = False
                if not holiday.mode_company_id:
                    holiday.mode_company_id = self.env.company.id
                holiday.category_id = False
            elif holiday.holiday_type == 'department':
                holiday.employee_ids = False
                holiday.mode_company_id = False
                holiday.category_id = False
            elif holiday.holiday_type == 'category':
                holiday.employee_ids = False
                holiday.mode_company_id = False
            else:
                holiday.employee_ids = self.env.context.get('default_employee_id') or holiday.employee_id or self.env.user.employee_id

    @api.depends('employee_id')
    def _compute_from_employee_id(self):
        for holiday in self:
            holiday.manager_id = holiday.employee_id.parent_id.id
            if holiday.employee_id.user_id != self.env.user and self._origin.employee_id != holiday.employee_id:
                holiday.holiday_status_id = False

    @api.depends('employee_id', 'holiday_type')
    def _compute_department_id(self):
        for holiday in self:
            if holiday.employee_id:
                holiday.department_id = holiday.employee_id.department_id
            elif holiday.holiday_type == 'department':
                if not holiday.department_id:
                    holiday.department_id = self.env.user.employee_id.department_id
            else:
                holiday.department_id = False

    @api.depends('date_from', 'date_to', 'holiday_status_id')
    def _compute_has_stress_day(self):
        date_from, date_to = min(self.mapped('date_from')), max(self.mapped('date_to'))
        resource_calendar_id = self.employee_id.resource_calendar_id or self.env.company.resource_calendar_id
        if date_from and date_to:
            stress_days = self.env['hr.leave.stress.day'].search([
                ('start_date', '<=', date_to.date()),
                ('end_date', '>=', date_from.date()),
                '|',
                    ('resource_calendar_id', '=', False),
                    ('resource_calendar_id', 'in', resource_calendar_id.ids),
            ])

            for leave in self:
                domain = [
                    ('start_date', '<=', leave.date_to.date()),
                    ('end_date', '>=', leave.date_from.date()),
                    '|',
                        ('resource_calendar_id', '=', False),
                        ('resource_calendar_id', '=', (leave.employee_id.resource_calendar_id or self.env.company.resource_calendar_id).id)
                ]

                if leave.holiday_status_id.company_id:
                    domain += [('company_id', '=', leave.holiday_status_id.company_id.id)]
                leave.has_stress_day = leave.date_from and leave.date_to and stress_days.filtered_domain(domain)
        else:
            self.has_stress_day = False

    @api.depends('date_from', 'date_to', 'employee_id')
    def _compute_number_of_days(self):
        for holiday in self:
            if holiday.date_from and holiday.date_to:
                holiday.number_of_days = holiday._get_number_of_days(holiday.date_from, holiday.date_to, holiday.employee_id.id)['days']
            else:
                holiday.number_of_days = 0

    @api.depends('tz')
    @api.depends_context('uid')
    def _compute_tz_mismatch(self):
        for leave in self:
            leave.tz_mismatch = leave.tz != self.env.user.tz

    @api.depends('employee_id', 'holiday_type', 'department_id.company_id.resource_calendar_id.tz', 'mode_company_id.resource_calendar_id.tz')
    def _compute_tz(self):
        for leave in self:
            tz = False
            if leave.holiday_type == 'employee':
                tz = leave.employee_id.tz
            elif leave.holiday_type == 'department':
                tz = leave.department_id.company_id.resource_calendar_id.tz
            elif leave.holiday_type == 'company':
                tz = leave.mode_company_id.resource_calendar_id.tz
            leave.tz = tz or self.env.company.resource_calendar_id.tz or self.env.user.tz or 'UTC'

    @api.depends('number_of_days')
    def _compute_number_of_days_display(self):
        for holiday in self:
            holiday.number_of_days_display = holiday.number_of_days

    def _get_calendar(self):
        self.ensure_one()
        return self.employee_id.resource_calendar_id or self.env.company.resource_calendar_id

    @api.depends('number_of_days')
    def _compute_number_of_hours_display(self):
        for holiday in self:
            calendar = holiday._get_calendar()
            if holiday.date_from and holiday.date_to:
                # Take attendances into account, in case the leave validated
                # Otherwise, this will result into number_of_hours = 0
                # and number_of_hours_display = 0 or (#day * calendar.hours_per_day),
                # which could be wrong if the employee doesn't work the same number
                # hours each day
                if holiday.state == 'validate':
                    start_dt = holiday.date_from
                    end_dt = holiday.date_to
                    if not start_dt.tzinfo:
                        start_dt = start_dt.replace(tzinfo=UTC)
                    if not end_dt.tzinfo:
                        end_dt = end_dt.replace(tzinfo=UTC)
                    resource = holiday.employee_id.resource_id
                    intervals = calendar._attendance_intervals_batch(start_dt, end_dt, resource)[resource.id] \
                                - calendar._leave_intervals_batch(start_dt, end_dt, None)[False]  # Substract Global Leaves
                    number_of_hours = sum((stop - start).total_seconds() / 3600 for start, stop, dummy in intervals)
                else:
                    number_of_hours = holiday._get_number_of_days(holiday.date_from, holiday.date_to, holiday.employee_id.id)['hours']
                holiday.number_of_hours_display = number_of_hours or (holiday.number_of_days * (calendar.hours_per_day or HOURS_PER_DAY))
            else:
                holiday.number_of_hours_display = 0

    @api.depends('number_of_hours_display', 'number_of_days_display')
    def _compute_duration_display(self):
        for leave in self:
            leave.duration_display = '%g %s' % (
                (float_round(leave.number_of_hours_display, precision_digits=2)
                if leave.leave_type_request_unit == 'hour'
                else float_round(leave.number_of_days_display, precision_digits=2)),
                _('hours') if leave.leave_type_request_unit == 'hour' else _('days'))

    @api.depends('number_of_hours_display')
    def _compute_number_of_hours_text(self):
        # YTI Note: All this because a readonly field takes all the width on edit mode...
        for leave in self:
            leave.number_of_hours_text = '%s%g %s%s' % (
                '' if leave.request_unit_half or leave.request_unit_hours else '(',
                float_round(leave.number_of_hours_display, precision_digits=2),
                _('Hours'),
                '' if leave.request_unit_half or leave.request_unit_hours else ')')

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
                if holiday.state == 'confirm' and holiday.validation_type == 'both':
                    holiday._check_approval_update('validate1')
                else:
                    holiday._check_approval_update('validate')
            except (AccessError, UserError):
                holiday.can_approve = False
            else:
                holiday.can_approve = True

    @api.depends_context('uid')
    @api.depends('state', 'employee_id')
    def _compute_can_cancel(self):
        now = fields.Datetime.now()
        for leave in self:
            leave.can_cancel = leave.id and leave.employee_id.user_id == self.env.user and leave.state == 'validate' and leave.date_from and leave.date_from > now

    @api.depends('state')
    def _compute_is_hatched(self):
        for holiday in self:
            holiday.is_striked = holiday.state == 'refuse'
            holiday.is_hatched = holiday.state not in ['refuse', 'validate']

    @api.depends('leave_type_support_document', 'attachment_ids')
    def _compute_supported_attachment_ids(self):
        for holiday in self:
            holiday.supported_attachment_ids = holiday.attachment_ids
            holiday.supported_attachment_ids_count = len(holiday.attachment_ids.ids)

    def _inverse_supported_attachment_ids(self):
        for holiday in self:
            holiday.supported_attachment_ids.write({
                'res_id': holiday.id,
            })

    @api.constrains('date_from', 'date_to', 'employee_id')
    def _check_date(self):
        if self.env.context.get('leave_skip_date_check', False):
            return

        all_employees = self.employee_id | self.employee_ids
        all_leaves = self.search([
            ('date_from', '<', max(self.mapped('date_to'))),
            ('date_to', '>', min(self.mapped('date_from'))),
            ('employee_id', 'in', all_employees.ids),
            ('id', 'not in', self.ids),
            ('state', 'not in', ['cancel', 'refuse']),
        ])
        for holiday in self:
            domain = [
                ('date_from', '<', holiday.date_to),
                ('date_to', '>', holiday.date_from),
                ('id', '!=', holiday.id),
                ('state', 'not in', ['cancel', 'refuse']),
            ]

            employee_ids = (holiday.employee_id | holiday.employee_ids).ids
            search_domain = domain + [('employee_id', 'in', employee_ids)]
            conflicting_holidays = all_leaves.filtered_domain(search_domain)

            if conflicting_holidays:
                conflicting_holidays_list = []
                # Do not display the name of the employee if the conflicting holidays have an employee_id.user_id equivalent to the user id
                holidays_only_have_uid = bool(holiday.employee_id)
                holiday_states = dict(conflicting_holidays.fields_get(allfields=['state'])['state']['selection'])
                for conflicting_holiday in conflicting_holidays:
                    conflicting_holiday_data = {}
                    conflicting_holiday_data['employee_name'] = conflicting_holiday.employee_id.name
                    conflicting_holiday_data['date_from'] = format_date(self.env, min(conflicting_holiday.mapped('date_from')))
                    conflicting_holiday_data['date_to'] = format_date(self.env, min(conflicting_holiday.mapped('date_to')))
                    conflicting_holiday_data['state'] = holiday_states[conflicting_holiday.state]
                    if conflicting_holiday.employee_id.user_id.id != self.env.uid:
                        holidays_only_have_uid = False
                    if conflicting_holiday_data not in conflicting_holidays_list:
                        conflicting_holidays_list.append(conflicting_holiday_data)
                if not conflicting_holidays_list:
                    return
                conflicting_holidays_strings = []
                if holidays_only_have_uid:
                    for conflicting_holiday_data in conflicting_holidays_list:
                        conflicting_holidays_string = _('From %(date_from)s To %(date_to)s - %(state)s',
                                                        date_from=conflicting_holiday_data['date_from'],
                                                        date_to=conflicting_holiday_data['date_to'],
                                                        state=conflicting_holiday_data['state'])
                        conflicting_holidays_strings.append(conflicting_holidays_string)
                    raise ValidationError(_('You can not set two time off that overlap on the same day.\nExisting time off:\n%s') %
                                          ('\n'.join(conflicting_holidays_strings)))
                for conflicting_holiday_data in conflicting_holidays_list:
                    conflicting_holidays_string = _('%(employee_name)s - From %(date_from)s To %(date_to)s - %(state)s',
                                                    employee_name=conflicting_holiday_data['employee_name'],
                                                    date_from=conflicting_holiday_data['date_from'],
                                                    date_to=conflicting_holiday_data['date_to'],
                                                    state=conflicting_holiday_data['state'])
                    conflicting_holidays_strings.append(conflicting_holidays_string)
                conflicting_employees = set(employee_ids) - set(conflicting_holidays.employee_id.ids)
                # Only one employee has a conflicting holiday
                if len(conflicting_employees) == len(employee_ids) - 1:
                    raise ValidationError(_('You can not set two time off that overlap on the same day for the same employee.\nExisting time off:\n%s') %
                                          ('\n'.join(conflicting_holidays_strings)))
                raise ValidationError(_('You can not set two time off that overlap on the same day for the same employees.\nExisting time off:\n%s') %
                                      ('\n'.join(conflicting_holidays_strings)))

    @api.constrains('state', 'number_of_days', 'holiday_status_id')
    def _check_holidays(self):
        for holiday in self:
            mapped_days = self.holiday_status_id.get_employees_days(holiday.employee_id.ids, holiday.date_from.date())
            if holiday.holiday_type != 'employee' or not holiday.employee_id or holiday.holiday_status_id.requires_allocation == 'no':
                continue
            leave_days = mapped_days[holiday.employee_id.id][holiday.holiday_status_id.id]
            if float_compare(leave_days['remaining_leaves'], 0, precision_digits=2) == -1 or float_compare(leave_days['virtual_remaining_leaves'], 0, precision_digits=2) == -1:
                raise ValidationError(_('The number of remaining time off is not sufficient for this time off type.\n'
                                        'Please also check the time off waiting for validation.'))

    @api.constrains('date_from', 'date_to', 'employee_id')
    def _check_date_state(self):
        if self.env.context.get('leave_skip_state_check'):
            return
        for holiday in self:
            if holiday.state in ['cancel', 'refuse', 'validate1', 'validate']:
                raise ValidationError(_("This modification is not allowed in the current state."))

    def _get_number_of_days_batch(self, date_from, date_to, employee_ids):
        """ Returns a float equals to the timedelta between two dates given as string."""
        employee = self.env['hr.employee'].browse(employee_ids)
        # We force the company in the domain as we are more than likely in a compute_sudo
        domain = [('company_id', 'in', self.env.company.ids + self.env.context.get('allowed_company_ids', []))]

        result = employee._get_work_days_data_batch(date_from, date_to, domain=domain)
        for employee_id in result:
            if self.request_unit_half and result[employee_id]['hours'] > 0:
                result[employee_id]['days'] = 0.5
        return result

    def _get_number_of_days(self, date_from, date_to, employee_id):
        """ Returns a float equals to the timedelta between two dates given as string."""
        if employee_id:
            return self._get_number_of_days_batch(date_from, date_to, employee_id)[employee_id]

        today_hours = self.env.company.resource_calendar_id.get_work_hours_count(
            datetime.combine(date_from.date(), time.min),
            datetime.combine(date_from.date(), time.max),
            False)

        hours = self.env.company.resource_calendar_id.get_work_hours_count(date_from, date_to)
        days = hours / (today_hours or HOURS_PER_DAY) if not self.request_unit_half else 0.5
        return {'days': days, 'hours': hours}

    def _adjust_date_based_on_tz(self, leave_date, hour):
        """ request_date_{from,to} are local to the user's tz but hour_{from,to} are in UTC.

        In some cases they are combined (assuming they are in the same tz) as a datetime. When
        that happens it's possible we need to adjust one of the dates. This function adjust the
        date, so that it can be passed to datetime().

        E.g. a leave in US/Pacific for one day:
        - request_date_from: 1st of Jan
        - request_date_to:   1st of Jan
        - hour_from:         15:00 (7:00 local)
        - hour_to:           03:00 (19:00 local) <-- this happens on the 2nd of Jan in UTC
        """
        user_tz = timezone(self.env.user.tz if self.env.user.tz else 'UTC')
        request_date_to_utc = UTC.localize(datetime.combine(leave_date, hour)).astimezone(user_tz).replace(tzinfo=None)
        if request_date_to_utc.date() < leave_date:
            return leave_date + timedelta(days=1)
        elif request_date_to_utc.date() > leave_date:
            return leave_date - timedelta(days=1)
        else:
            return leave_date

    ####################################################
    # ORM Overrides methods
    ####################################################

    def onchange(self, values, field_name, field_onchange):
        # Try to force the leave_type name_get when creating new records
        # This is called right after pressing create and returns the name_get for
        # most fields in the view.
        if field_onchange.get('employee_id') and 'employee_id' not in self._context and values:
            employee_id = get_employee_from_context(values, self._context, self.env.user.employee_id.id)
            self = self.with_context(employee_id=employee_id)
        return super().onchange(values, field_name, field_onchange)

    def name_get(self):
        res = []
        for leave in self:
            if self.env.context.get('short_name'):
                if leave.leave_type_request_unit == 'hour':
                    res.append((leave.id, _("%s : %.2f hours") % (leave.name or leave.holiday_status_id.name, leave.number_of_hours_display)))
                else:
                    res.append((leave.id, _("%s : %.2f days") % (leave.name or leave.holiday_status_id.name, leave.number_of_days)))
            else:
                if leave.holiday_type == 'company':
                    target = leave.mode_company_id.name
                elif leave.holiday_type == 'department':
                    target = leave.department_id.name
                elif leave.holiday_type == 'category':
                    target = leave.category_id.name
                elif leave.employee_id:
                    target = leave.employee_id.name
                else:
                    target = ', '.join(leave.employee_ids.mapped('name'))
                if leave.leave_type_request_unit == 'hour':
                    if self.env.context.get('hide_employee_name') and 'employee_id' in self.env.context.get('group_by', []):
                        res.append((
                            leave.id,
                            _("%(person)s on %(leave_type)s: %(duration).2f hours on %(date)s",
                                person=target,
                                leave_type=leave.holiday_status_id.name,
                                duration=leave.number_of_hours_display,
                                date=fields.Date.to_string(leave.date_from),
                            )
                        ))
                    else:
                        user_tz = timezone(leave.tz)
                        date_from_utc = leave.date_from and leave.date_from.astimezone(user_tz).date()
                        res.append((
                            leave.id,
                            _("%(person)s on %(leave_type)s: %(duration).2f hours on %(date)s",
                                person=target,
                                leave_type=leave.holiday_status_id.name,
                                duration=leave.number_of_hours_display,
                                date=fields.Date.to_string(date_from_utc),
                            )
                        ))
                else:
                    display_date = fields.Date.to_string(leave.date_from)
                    if leave.number_of_days > 1:
                        display_date += ' / %s' % fields.Date.to_string(leave.date_to)
                    if self.env.context.get('hide_employee_name') and 'employee_id' in self.env.context.get('group_by', []):
                        res.append((
                            leave.id,
                            _("%(leave_type)s: %(duration).2f days (%(start)s)",
                                leave_type=leave.holiday_status_id.name,
                                duration=leave.number_of_days,
                                start=display_date,
                            )
                        ))
                    else:
                        res.append((
                            leave.id,
                            _("%(person)s on %(leave_type)s: %(duration).2f days (%(start)s)",
                                person=target,
                                leave_type=leave.holiday_status_id.name,
                                duration=leave.number_of_days,
                                start=display_date,
                            )
                        ))
        return res

    def add_follower(self, employee_id):
        employee = self.env['hr.employee'].browse(employee_id)
        if employee.user_id:
            self.message_subscribe(partner_ids=employee.user_id.partner_id.ids)

    @api.constrains('holiday_allocation_id')
    def _check_allocation_id(self):
        # Deprecated as part of https://github.com/odoo/odoo/pull/96545
        # TODO: remove in master
        return

    @api.constrains('holiday_allocation_id', 'date_to', 'date_from')
    def _check_leave_type_validity(self):
        # Deprecated as part of https://github.com/odoo/odoo/pull/96545
        # TODO: remove in master
        return

    @api.constrains('date_from', 'date_to')
    def _check_stress_day(self):
        is_leave_user = self.user_has_groups('hr_holidays.group_hr_holidays_user')
        if not is_leave_user and any(leave.has_stress_day for leave in self):
            raise ValidationError(_('You are not allowed to request a time off on a Stress Day.'))

    def _check_double_validation_rules(self, employees, state):
        if self.user_has_groups('hr_holidays.group_hr_holidays_manager'):
            return

        is_leave_user = self.user_has_groups('hr_holidays.group_hr_holidays_user')
        if state == 'validate1':
            employees = employees.filtered(lambda employee: employee.leave_manager_id != self.env.user)
            if employees and not is_leave_user:
                raise AccessError(_('You cannot first approve a time off for %s, because you are not his time off manager', employees[0].name))
        elif state == 'validate' and not is_leave_user:
            # Is probably handled via ir.rule
            raise AccessError(_('You don\'t have the rights to apply second approval on a time off request'))

    @api.model_create_multi
    def create(self, vals_list):
        leave_date_employees = defaultdict(list)
        employee_ids = []
        for values in vals_list:
            if values.get('employee_id'):
                employee_ids.append(values['employee_id'])
                if values.get('date_from') and values.get('date_to'):
                    date_from = fields.Datetime.to_datetime(values['date_from'])
                    date_to = fields.Datetime.to_datetime(values['date_to'])
                    if values['employee_id'] not in leave_date_employees[(date_from, date_to)]:
                        leave_date_employees[(date_from, date_to)].append(values['employee_id'])
        employees = self.env['hr.employee'].browse(employee_ids)
        if self._context.get('leave_compute_date_from_to') and employees:
            employee_leave_date_duration = defaultdict(dict)
            for (date_from, date_to), employee_ids in leave_date_employees.items():
                employee_leave_date_duration[(date_from, date_to)] = self._get_number_of_days_batch(date_from, date_to, employee_ids)
            for values in vals_list:
                employee_id = values.get('employee_id')
                if employee_id and values.get('date_from') and values.get('date_to'):
                    date_from = values.get('date_from')
                    date_to = values.get('date_to')
                    employee = employees.filtered(lambda emp: emp.id == employee_id)
                    attendance_from, attendance_to = self._get_attendances(employee, date_from.date(), date_to.date())
                    hour_from = max(values['date_from'].replace(tzinfo=UTC).astimezone(timezone(self.env.user.tz)).time(), float_to_time(attendance_from.hour_from))
                    hour_to = min(values['date_to'].replace(tzinfo=UTC).astimezone(timezone(self.env.user.tz)).time(), float_to_time(attendance_to.hour_to))
                    hour_from = hour_from.hour + hour_from.minute / 60
                    hour_to = hour_to.hour + hour_to.minute / 60

                    values['date_from'] = self._get_start_or_end_from_attendance(hour_from, date_from.date(), employee)
                    values['date_to'] = self._get_start_or_end_from_attendance(hour_to, date_to.date(), employee)
                    values['request_date_from'], values['request_date_to'] = values['date_from'].date(), values['date_to'].date()
                    values['number_of_days'] = employee_leave_date_duration[(date_from, date_to)][values['employee_id']]['days']

        """ Override to avoid automatic logging of creation """
        if not self._context.get('leave_fast_create'):
            leave_types = self.env['hr.leave.type'].browse([values.get('holiday_status_id') for values in vals_list if values.get('holiday_status_id')])
            mapped_validation_type = {leave_type.id: leave_type.leave_validation_type for leave_type in leave_types}

            for values in vals_list:
                employee_id = values.get('employee_id', False)
                leave_type_id = values.get('holiday_status_id')
                # Handle automatic department_id
                if not values.get('department_id'):
                    values.update({'department_id': employees.filtered(lambda emp: emp.id == employee_id).department_id.id})

                # Handle no_validation
                if mapped_validation_type[leave_type_id] == 'no_validation':
                    values.update({'state': 'confirm'})

                if 'state' not in values:
                    # To mimic the behavior of compute_state that was always triggered, as the field was readonly
                    values['state'] = 'confirm' if mapped_validation_type[leave_type_id] != 'no_validation' else 'draft'

                # Handle double validation
                if mapped_validation_type[leave_type_id] == 'both':
                    self._check_double_validation_rules(employee_id, values.get('state', False))

        holidays = super(HolidaysRequest, self.with_context(mail_create_nosubscribe=True)).create(vals_list)

        for holiday in holidays:
            if not self._context.get('leave_fast_create'):
                # Everything that is done here must be done using sudo because we might
                # have different create and write rights
                # eg : holidays_user can create a leave request with validation_type = 'manager' for someone else
                # but they can only write on it if they are leave_manager_id
                holiday_sudo = holiday.sudo()
                holiday_sudo.add_follower(employee_id)
                if holiday.validation_type == 'manager':
                    holiday_sudo.message_subscribe(partner_ids=holiday.employee_id.leave_manager_id.partner_id.ids)
                if holiday.validation_type == 'no_validation':
                    # Automatic validation should be done in sudo, because user might not have the rights to do it by himself
                    holiday_sudo.action_validate()
                    holiday_sudo.message_subscribe(partner_ids=[holiday._get_responsible_for_approval().partner_id.id])
                    holiday_sudo.message_post(body=_("The time off has been automatically approved"), subtype_xmlid="mail.mt_comment") # Message from OdooBot (sudo)
                elif not self._context.get('import_file'):
                    holiday_sudo.activity_update()
        return holidays

    def write(self, values):
        if 'active' in values and not self.env.context.get('from_cancel_wizard'):
            raise UserError(_("You can't manually archive/unarchive a time off."))

        is_officer = self.env.user.has_group('hr_holidays.group_hr_holidays_user') or self.env.is_superuser()
        if not is_officer and values.keys() - {'supported_attachment_ids', 'message_main_attachment_id'}:
            if any(hol.date_from.date() < fields.Date.today() and hol.employee_id.leave_manager_id != self.env.user for hol in self):
                raise UserError(_('You must have manager rights to modify/validate a time off that already begun'))

        # Unlink existing resource.calendar.leaves for validated time off
        if 'state' in values and values['state'] != 'validate':
            validated_leaves = self.filtered(lambda l: l.state == 'validate')
            validated_leaves._remove_resource_leave()

        employee_id = values.get('employee_id', False)
        if not self.env.context.get('leave_fast_create'):
            if values.get('state'):
                self._check_approval_update(values['state'])
                if any(holiday.validation_type == 'both' for holiday in self):
                    if values.get('employee_id'):
                        employees = self.env['hr.employee'].browse(values.get('employee_id'))
                    else:
                        employees = self.mapped('employee_id')
                    self._check_double_validation_rules(employees, values['state'])
            if 'date_from' in values:
                values['request_date_from'] = values['date_from']
            if 'date_to' in values:
                values['request_date_to'] = values['date_to']
        result = super(HolidaysRequest, self).write(values)
        if not self.env.context.get('leave_fast_create'):
            for holiday in self:
                if employee_id:
                    holiday.add_follower(employee_id)

        return result

    @api.ondelete(at_uninstall=False)
    def _unlink_if_correct_states(self):
        error_message = _('You cannot delete a time off which is in %s state')
        state_description_values = {elem[0]: elem[1] for elem in self._fields['state']._description_selection(self.env)}
        now = fields.Datetime.now()

        if not self.user_has_groups('hr_holidays.group_hr_holidays_user'):
            for hol in self:
                if hol.state not in ['draft', 'confirm']:
                    raise UserError(error_message % state_description_values.get(self[:1].state))
                if hol.date_from < now:
                    raise UserError(_('You cannot delete a time off which is in the past'))
                if hol.employee_ids and not hol.employee_id:
                    raise UserError(_('You cannot delete a time off assigned to several employees'))
        else:
            for holiday in self.filtered(lambda holiday: holiday.state not in ['draft', 'cancel', 'confirm']):
                raise UserError(error_message % (state_description_values.get(holiday.state),))

    def unlink(self):
        return super(HolidaysRequest, self.with_context(leave_skip_date_check=True)).unlink()

    def copy_data(self, default=None):
        if default and 'date_from' in default and 'date_to' in default:
            default['request_date_from'] = default.get('date_from')
            default['request_date_to'] = default.get('date_to')
            return super().copy_data(default)
        raise UserError(_('A time off cannot be duplicated.'))

    def _get_mail_redirect_suggested_company(self):
        return self.holiday_status_id.company_id

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        if not self.user_has_groups('hr_holidays.group_hr_holidays_user') and 'private_name' in groupby:
            raise UserError(_('Such grouping is not allowed.'))
        return super(HolidaysRequest, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)

    ####################################################
    # Business methods
    ####################################################

    def _prepare_resource_leave_vals_list(self):
        """Hook method for others to inject data
        """
        return [{
            'name': _("%s: Time Off", leave.employee_id.name),
            'date_from': leave.date_from,
            'holiday_id': leave.id,
            'date_to': leave.date_to,
            'resource_id': leave.employee_id.resource_id.id,
            'calendar_id': leave.employee_id.resource_calendar_id.id,
            'time_type': leave.holiday_status_id.time_type,
        } for leave in self]

    def _create_resource_leave(self):
        """ This method will create entry in resource calendar time off object at the time of holidays validated
        :returns: created `resource.calendar.leaves`
        """
        vals_list = self._prepare_resource_leave_vals_list()
        return self.env['resource.calendar.leaves'].sudo().create(vals_list)

    def _remove_resource_leave(self):
        """ This method will create entry in resource calendar time off object at the time of holidays cancel/removed """
        return self.env['resource.calendar.leaves'].search([('holiday_id', 'in', self.ids)]).unlink()

    def _validate_leave_request(self):
        """ Validate time off requests (holiday_type='employee')
        by creating a calendar event and a resource time off. """
        holidays = self.filtered(lambda request: request.holiday_type == 'employee' and request.employee_id)
        holidays._create_resource_leave()
        meeting_holidays = holidays.filtered(lambda l: l.holiday_status_id.create_calendar_meeting)
        meetings = self.env['calendar.event']
        if meeting_holidays:
            meeting_values_for_user_id = meeting_holidays._prepare_holidays_meeting_values()
            Meeting = self.env['calendar.event']
            for user_id, meeting_values in meeting_values_for_user_id.items():
                meetings += Meeting.with_user(user_id or self.env.uid).with_context(
                                no_mail_to_attendees=True,
                                calendar_no_videocall=True,
                                active_model=self._name
                            ).create(meeting_values)
        Holiday = self.env['hr.leave']
        for meeting in meetings:
            Holiday.browse(meeting.res_id).meeting_id = meeting

    def _prepare_holidays_meeting_values(self):
        result = defaultdict(list)
        company_calendar = self.env.company.resource_calendar_id
        for holiday in self:
            calendar = holiday.employee_id.resource_calendar_id or company_calendar
            user = holiday.user_id
            if holiday.leave_type_request_unit == 'hour':
                meeting_name = _("%s on Time Off : %.2f hour(s)") % (holiday.employee_id.name or holiday.category_id.name, holiday.number_of_hours_display)
            else:
                meeting_name = _("%s on Time Off : %.2f day(s)") % (holiday.employee_id.name or holiday.category_id.name, holiday.number_of_days)
            meeting_values = {
                'name': meeting_name,
                'duration': holiday.number_of_days * (calendar.hours_per_day or HOURS_PER_DAY),
                'description': holiday.notes,
                'user_id': user.id,
                'start': holiday.date_from,
                'stop': holiday.date_to,
                'allday': False,
                'privacy': 'confidential',
                'event_tz': user.tz,
                'activity_ids': [(5, 0, 0)],
                'res_id': holiday.id,
            }
            # Add the partner_id (if exist) as an attendee
            if user and user.partner_id:
                meeting_values['partner_ids'] = [
                    (4, user.partner_id.id)]
            result[user.id].append(meeting_values)
        return result

    def _prepare_employees_holiday_values(self, employees):
        self.ensure_one()
        work_days_data = employees._get_work_days_data_batch(self.date_from, self.date_to)
        return [{
            'name': self.name,
            'holiday_type': 'employee',
            'holiday_status_id': self.holiday_status_id.id,
            'date_from': self.date_from,
            'date_to': self.date_to,
            'request_date_from': self.request_date_from,
            'request_date_to': self.request_date_to,
            'notes': self.notes,
            'number_of_days': work_days_data[employee.id]['days'],
            'parent_id': self.id,
            'employee_id': employee.id,
            'employee_ids': employee,
            'state': 'validate',
        } for employee in employees if work_days_data[employee.id]['days']]

    def action_cancel(self):
        self.ensure_one()

        return {
            'name': _('Cancel Time Off'),
            'type': 'ir.actions.act_window',
            'target': 'new',
            'res_model': 'hr.holidays.cancel.leave',
            'view_mode': 'form',
            'views': [[False, 'form']],
            'context': {
                'default_leave_id': self.id,
            }
        }

    def action_draft(self):
        if any(holiday.state not in ['confirm', 'refuse'] for holiday in self):
            raise UserError(_('Time off request state must be "Refused" or "To Approve" in order to be reset to draft.'))
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

    def action_confirm(self):
        if self.filtered(lambda holiday: holiday.state != 'draft'):
            raise UserError(_('Time off request must be in Draft state ("To Submit") in order to confirm it.'))
        self.write({'state': 'confirm'})
        holidays = self.filtered(lambda leave: leave.validation_type == 'no_validation')
        if holidays:
            # Automatic validation should be done in sudo, because user might not have the rights to do it by himself
            holidays.sudo().action_validate()
        self.activity_update()
        return True

    def action_approve(self):
        # if validation_type == 'both': this method is the first approval approval
        # if validation_type != 'both': this method calls action_validate() below
        if any(holiday.state != 'confirm' for holiday in self):
            raise UserError(_('Time off request must be confirmed ("To Approve") in order to approve it.'))

        current_employee = self.env.user.employee_id
        self.filtered(lambda hol: hol.validation_type == 'both').write({'state': 'validate1', 'first_approver_id': current_employee.id})


        # Post a second message, more verbose than the tracking message
        for holiday in self.filtered(lambda holiday: holiday.employee_id.user_id):
            user_tz = timezone(holiday.tz)
            utc_tz = pytz.utc.localize(holiday.date_from).astimezone(user_tz)
            holiday.message_post(
                body=_(
                    'Your %(leave_type)s planned on %(date)s has been accepted',
                    leave_type=holiday.holiday_status_id.display_name,
                    date=utc_tz.replace(tzinfo=None)
                ),
                partner_ids=holiday.employee_id.user_id.partner_id.ids)

        self.filtered(lambda hol: not hol.validation_type == 'both').action_validate()
        if not self.env.context.get('leave_fast_create'):
            self.activity_update()
        return True

    def _get_leaves_on_public_holiday(self):
        return self.filtered(lambda l: l.employee_id and not l.number_of_days)

    def action_validate(self):
        current_employee = self.env.user.employee_id
        leaves = self._get_leaves_on_public_holiday()
        if leaves:
            raise ValidationError(_('The following employees are not supposed to work during that period:\n %s') % ','.join(leaves.mapped('employee_id.name')))

        if any(holiday.state not in ['confirm', 'validate1'] and holiday.validation_type != 'no_validation' for holiday in self):
            raise UserError(_('Time off request must be confirmed in order to approve it.'))

        self.write({'state': 'validate'})

        leaves_second_approver = self.env['hr.leave']
        leaves_first_approver = self.env['hr.leave']

        for leave in self:
            if leave.validation_type == 'both':
                leaves_second_approver += leave
            else:
                leaves_first_approver += leave

            if leave.holiday_type != 'employee' or\
                (leave.holiday_type == 'employee' and len(leave.employee_ids) > 1):
                if leave.holiday_type == 'employee':
                    employees = leave.employee_ids
                elif leave.holiday_type == 'category':
                    employees = leave.category_id.employee_ids
                elif leave.holiday_type == 'company':
                    employees = self.env['hr.employee'].search([('company_id', '=', leave.mode_company_id.id)])
                else:
                    employees = leave.department_id.member_ids

                conflicting_leaves = self.env['hr.leave'].with_context(
                    tracking_disable=True,
                    mail_activity_automation_skip=True,
                    leave_fast_create=True
                ).search([
                    ('date_from', '<=', leave.date_to),
                    ('date_to', '>', leave.date_from),
                    ('state', 'not in', ['cancel', 'refuse']),
                    ('holiday_type', '=', 'employee'),
                    ('employee_id', 'in', employees.ids)])

                if conflicting_leaves:
                    # YTI: More complex use cases could be managed in master
                    if leave.leave_type_request_unit != 'day' or any(l.leave_type_request_unit == 'hour' for l in conflicting_leaves):
                        raise ValidationError(_('You can not have 2 time off that overlaps on the same day.'))

                    # keep track of conflicting leaves states before refusal
                    target_states = {l.id: l.state for l in conflicting_leaves}
                    conflicting_leaves.action_refuse()
                    split_leaves_vals = []
                    for conflicting_leave in conflicting_leaves:
                        if conflicting_leave.leave_type_request_unit == 'half_day' and conflicting_leave.request_unit_half:
                            continue

                        # Leaves in days
                        if conflicting_leave.date_from < leave.date_from:
                            before_leave_vals = conflicting_leave.copy_data({
                                'date_from': conflicting_leave.date_from.date(),
                                'date_to': leave.date_from.date() + timedelta(days=-1),
                                'state': target_states[conflicting_leave.id],
                            })[0]
                            before_leave = self.env['hr.leave'].new(before_leave_vals)
                            before_leave._compute_date_from_to()

                            # Could happen for part-time contract, that time off is not necessary
                            # anymore.
                            # Imagine you work on monday-wednesday-friday only.
                            # You take a time off on friday.
                            # We create a company time off on friday.
                            # By looking at the last attendance before the company time off
                            # start date to compute the date_to, you would have a date_from > date_to.
                            # Just don't create the leave at that time. That's the reason why we use
                            # new instead of create. As the leave is not actually created yet, the sql
                            # constraint didn't check date_from < date_to yet.
                            if before_leave.date_from < before_leave.date_to:
                                split_leaves_vals.append(before_leave._convert_to_write(before_leave._cache))
                        if conflicting_leave.date_to > leave.date_to:
                            after_leave_vals = conflicting_leave.copy_data({
                                'date_from': leave.date_to.date() + timedelta(days=1),
                                'date_to': conflicting_leave.date_to.date(),
                                'state': target_states[conflicting_leave.id],
                            })[0]
                            after_leave = self.env['hr.leave'].new(after_leave_vals)
                            after_leave._compute_date_from_to()
                            # Could happen for part-time contract, that time off is not necessary
                            # anymore.
                            if after_leave.date_from < after_leave.date_to:
                                split_leaves_vals.append(after_leave._convert_to_write(after_leave._cache))

                    split_leaves = self.env['hr.leave'].with_context(
                        tracking_disable=True,
                        mail_activity_automation_skip=True,
                        leave_fast_create=True,
                        leave_skip_state_check=True
                    ).create(split_leaves_vals)

                    split_leaves.filtered(lambda l: l.state in 'validate')._validate_leave_request()

                values = leave._prepare_employees_holiday_values(employees)
                leaves = self.env['hr.leave'].with_context(
                    tracking_disable=True,
                    mail_activity_automation_skip=True,
                    leave_fast_create=True,
                    no_calendar_sync=True,
                    leave_skip_state_check=True,
                    # date_from and date_to are computed based on the employee tz
                    # If _compute_date_from_to is used instead, it will trigger _compute_number_of_days
                    # and create a conflict on the number of days calculation between the different leaves
                    leave_compute_date_from_to=True,
                ).create(values)

                leaves._validate_leave_request()

        leaves_second_approver.write({'second_approver_id': current_employee.id})
        leaves_first_approver.write({'first_approver_id': current_employee.id})

        employee_requests = self.filtered(lambda hol: hol.holiday_type == 'employee')
        employee_requests._validate_leave_request()
        if not self.env.context.get('leave_fast_create'):
            employee_requests.filtered(lambda holiday: holiday.validation_type != 'no_validation').activity_update()
        return True

    def action_refuse(self):
        current_employee = self.env.user.employee_id
        if any(holiday.state not in ['draft', 'confirm', 'validate', 'validate1'] for holiday in self):
            raise UserError(_('Time off request must be confirmed or validated in order to refuse it.'))

        validated_holidays = self.filtered(lambda hol: hol.state == 'validate1')
        validated_holidays.write({'state': 'refuse', 'first_approver_id': current_employee.id})
        (self - validated_holidays).write({'state': 'refuse', 'second_approver_id': current_employee.id})
        # Delete the meeting
        self.mapped('meeting_id').write({'active': False})
        # If a category that created several holidays, cancel all related
        linked_requests = self.mapped('linked_request_ids')
        if linked_requests:
            linked_requests.action_refuse()

        # Post a second message, more verbose than the tracking message
        for holiday in self:
            if holiday.employee_id.user_id:
                holiday.message_post(
                    body=_('Your %(leave_type)s planned on %(date)s has been refused', leave_type=holiday.holiday_status_id.display_name, date=holiday.date_from),
                    partner_ids=holiday.employee_id.user_id.partner_id.ids)

        self.activity_update()
        return True

    def _action_user_cancel(self, reason):
        self.ensure_one()
        if not self.can_cancel:
            raise ValidationError(_('This time off cannot be canceled.'))

        self._force_cancel(reason, 'mail.mt_note')

    def _force_cancel(self, reason, msg_subtype='mail.mt_comment'):
        for leave in self:
            leave.message_post(
                body=_('The time off has been canceled: %s', reason),
                subtype_xmlid=msg_subtype
            )

        leave_sudo = self.sudo()
        leave_sudo.with_context(from_cancel_wizard=True).active = False
        leave_sudo._remove_resource_leave()

    def action_documents(self):
        domain = [('id', 'in', self.attachment_ids.ids)]
        return {
            'name': _("Supporting Documents"),
            'type': 'ir.actions.act_window',
            'res_model': 'ir.attachment',
            'context': {'create': False},
            'view_mode': 'kanban',
            'domain': domain
        }

    def _check_approval_update(self, state):
        """ Check if target state is achievable. """
        if self.env.is_superuser():
            return

        current_employee = self.env.user.employee_id
        is_officer = self.env.user.has_group('hr_holidays.group_hr_holidays_user')
        is_manager = self.env.user.has_group('hr_holidays.group_hr_holidays_manager')

        for holiday in self:
            val_type = holiday.validation_type

            if not is_manager and state != 'confirm':
                if state == 'draft':
                    if holiday.state == 'refuse':
                        raise UserError(_('Only a Time Off Manager can reset a refused leave.'))
                    if holiday.date_from and holiday.date_from.date() <= fields.Date.today():
                        raise UserError(_('Only a Time Off Manager can reset a started leave.'))
                    if holiday.employee_id != current_employee:
                        raise UserError(_('Only a Time Off Manager can reset other people leaves.'))
                else:
                    if val_type == 'no_validation' and current_employee == holiday.employee_id:
                        continue
                    # use ir.rule based first access check: department, members, ... (see security.xml)
                    holiday.check_access_rule('write')

                    # This handles states validate1 validate and refuse
                    if holiday.employee_id == current_employee:
                        raise UserError(_('Only a Time Off Manager can approve/refuse its own requests.'))

                    if (state == 'validate1' and val_type == 'both') and holiday.holiday_type == 'employee':
                        if not is_officer and self.env.user != holiday.employee_id.leave_manager_id:
                            raise UserError(_('You must be either %s\'s manager or Time off Manager to approve this leave') % (holiday.employee_id.name))

                    if (state == 'validate' and val_type == 'manager') and self.env.user != holiday.employee_id.leave_manager_id:
                        raise UserError(_('You must be %s\'s Manager to approve this leave', holiday.employee_id.name))

                    if not is_officer and (state == 'validate' and val_type == 'hr') and holiday.holiday_type == 'employee':
                        raise UserError(_('You must either be a Time off Officer or Time off Manager to approve this leave'))

    ###################################################
    # Leave modification methods
    ###################################################

    def _split_leave_on_gto(self, gto): #gto = global time off
        self.ensure_one()

        leave_start = date_utils.start_of(self.date_from, 'day')
        leave_end = date_utils.end_of(self.date_to - timedelta(seconds=1), 'day')
        gto_start = date_utils.start_of(gto['date_from'], 'day')
        gto_end = date_utils.end_of(gto['date_to'], 'day')
        leave_tz = timezone(self.employee_id.resource_id.tz)

        if gto_start <= leave_start\
                and gto_end > leave_start\
                and gto_end < leave_end:
            self.write({
                'date_from': leave_tz.localize(gto_end + timedelta(seconds=1))\
                        .astimezone(UTC).replace(tzinfo=None)
            })
            return self.env['hr.leave']
        if gto_start > leave_start\
                and gto_end < leave_end:
            copys = {
                'date_from': self.date_from,
                'date_to': leave_tz.localize(gto_start - timedelta(seconds=1))\
                        .astimezone(UTC).replace(tzinfo=None)
            }
            self.write({
                'date_from': leave_tz.localize(gto_end + timedelta(seconds=1))\
                        .astimezone(UTC).replace(tzinfo=None)
            })
            return self.copy(copys)
        if gto_start > leave_start\
                and gto_start < leave_end\
                and gto_end >= leave_end:
            self.write({
                'date_to': leave_tz.localize(gto_start - timedelta(seconds=1))\
                        .astimezone(UTC).replace(tzinfo=None)
            })
            return self.env['hr.leave']

    def split_leave(self, time_domain_dict):
        self.ensure_one()

        new_leaves = self.env['hr.leave']
        for global_time_off in sorted(
                filter(lambda r: r['date_to'] > self.date_from and r['date_from'] < self.date_to, time_domain_dict),
                key=lambda r: r['date_from']):
            new_leave = self._split_leave_on_gto(global_time_off)
            if new_leave:
                new_leaves |= new_leave
        return new_leaves

    # ------------------------------------------------------------
    # Activity methods
    # ------------------------------------------------------------

    def _get_responsible_for_approval(self):
        self.ensure_one()

        responsible = self.env.user

        if self.holiday_type != 'employee':
            return responsible

        if self.validation_type == 'manager' or (self.validation_type == 'both' and self.state == 'confirm'):
            if self.employee_id.leave_manager_id:
                responsible = self.employee_id.leave_manager_id
            elif self.employee_id.parent_id.user_id:
                responsible = self.employee_id.parent_id.user_id
        elif self.validation_type == 'hr' or (self.validation_type == 'both' and self.state == 'validate1'):
            if self.holiday_status_id.responsible_id:
                responsible = self.holiday_status_id.responsible_id

        return responsible

    def activity_update(self):
        to_clean, to_do = self.env['hr.leave'], self.env['hr.leave']
        for holiday in self:
            note = _(
                'New %(leave_type)s Request created by %(user)s',
                leave_type=holiday.holiday_status_id.name,
                user=holiday.create_uid.name,
            )
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

    def _notify_change(self, message, subtype_xmlid='mail.mt_note'):
        for leave in self:
            leave.message_post(body=message, subtype_xmlid=subtype_xmlid)

            recipient = None
            if leave.user_id:
                recipient = leave.user_id.partner_id.id
            elif leave.employee_id:
                recipient = leave.employee_id.address_home_id.id

            if recipient:
                self.env['mail.thread'].sudo().message_notify(body=message, partner_ids=[recipient])

    def _track_subtype(self, init_values):
        if 'state' in init_values and self.state == 'validate':
            leave_notif_subtype = self.holiday_status_id.leave_notif_subtype_id
            return leave_notif_subtype or self.env.ref('hr_holidays.mt_leave')
        return super(HolidaysRequest, self)._track_subtype(init_values)

    def _notify_get_recipients_groups(self, msg_vals=None):
        """ Handle HR users and officers recipients that can validate or refuse holidays
        directly from email. """
        groups = super(HolidaysRequest, self)._notify_get_recipients_groups(msg_vals=msg_vals)
        local_msg_vals = dict(msg_vals or {})

        self.ensure_one()
        hr_actions = []
        if self.state == 'confirm':
            app_action = self._notify_get_action_link('controller', controller='/leave/validate', **local_msg_vals)
            hr_actions += [{'url': app_action, 'title': _('Approve')}]
        if self.state in ['confirm', 'validate', 'validate1']:
            ref_action = self._notify_get_action_link('controller', controller='/leave/refuse', **local_msg_vals)
            hr_actions += [{'url': ref_action, 'title': _('Refuse')}]

        holiday_user_group_id = self.env.ref('hr_holidays.group_hr_holidays_user').id
        new_group = (
            'group_hr_holidays_user',
            lambda pdata: pdata['type'] == 'user' and holiday_user_group_id in pdata['groups'],
            {'actions': hr_actions}
        )

        return [new_group] + groups

    def message_subscribe(self, partner_ids=None, subtype_ids=None):
        # due to record rule can not allow to add follower and mention on validated leave so subscribe through sudo
        if self.state in ['validate', 'validate1']:
            self.check_access_rights('read')
            self.check_access_rule('read')
            return super(HolidaysRequest, self.sudo()).message_subscribe(partner_ids=partner_ids, subtype_ids=subtype_ids)
        return super(HolidaysRequest, self).message_subscribe(partner_ids=partner_ids, subtype_ids=subtype_ids)

    @api.model
    def get_unusual_days(self, date_from, date_to=None):
        return self.env.user.employee_id.sudo(False)._get_unusual_days(date_from, date_to)

    def _get_start_or_end_from_attendance(self, hour, date, employee):
        hour = float_to_time(float(hour))
        compensated_request_date = self._adjust_date_based_on_tz(date, hour)
        holiday_tz = timezone(employee.tz or self.env.user.tz)
        return holiday_tz.localize(datetime.combine(compensated_request_date, hour)).astimezone(UTC).replace(tzinfo=None)

    def _get_attendances(self, employee, request_date_from, request_date_to):
        resource_calendar_id = employee.resource_calendar_id or self.env.company.resource_calendar_id
        domain = [('calendar_id', '=', resource_calendar_id.id), ('display_type', '=', False)]
        attendances = self.env['resource.calendar.attendance'].read_group(domain,
            ['ids:array_agg(id)', 'hour_from:min(hour_from)', 'hour_to:max(hour_to)',
             'week_type', 'dayofweek', 'day_period'],
            ['week_type', 'dayofweek', 'day_period'], lazy=False)

        # Must be sorted by dayofweek ASC and day_period DESC
        attendances = sorted([DummyAttendance(group['hour_from'], group['hour_to'], group['dayofweek'], group['day_period'], group['week_type']) for group in attendances], key=lambda att: (att.dayofweek, att.day_period != 'morning'))

        default_value = DummyAttendance(0, 0, 0, 'morning', False)

        if resource_calendar_id.two_weeks_calendar:
            # find week type of start_date
            start_week_type = self.env['resource.calendar.attendance'].get_week_type(request_date_from)
            attendance_actual_week = [att for att in attendances if att.week_type is False or int(att.week_type) == start_week_type]
            attendance_actual_next_week = [att for att in attendances if att.week_type is False or int(att.week_type) != start_week_type]
            # First, add days of actual week coming after date_from
            attendance_filtred = [att for att in attendance_actual_week if int(att.dayofweek) >= request_date_from.weekday()]
            # Second, add days of the other type of week
            attendance_filtred += list(attendance_actual_next_week)
            # Third, add days of actual week (to consider days that we have remove first because they coming before date_from)
            attendance_filtred += list(attendance_actual_week)
            end_week_type = self.env['resource.calendar.attendance'].get_week_type(request_date_to)
            attendance_actual_week = [att for att in attendances if att.week_type is False or int(att.week_type) == end_week_type]
            attendance_actual_next_week = [att for att in attendances if att.week_type is False or int(att.week_type) != end_week_type]
            attendance_filtred_reversed = list(reversed([att for att in attendance_actual_week if int(att.dayofweek) <= request_date_to.weekday()]))
            attendance_filtred_reversed += list(reversed(attendance_actual_next_week))
            attendance_filtred_reversed += list(reversed(attendance_actual_week))

            # find first attendance coming after first_day
            attendance_from = attendance_filtred[0]
            # find last attendance coming before last_day
            attendance_to = attendance_filtred_reversed[0]
        else:
            # find first attendance coming after first_day
            attendance_from = next((att for att in attendances if int(att.dayofweek) >= request_date_from.weekday()), attendances[0] if attendances else default_value)
            # find last attendance coming before last_day
            attendance_to = next((att for att in reversed(attendances) if int(att.dayofweek) <= request_date_to.weekday()), attendances[-1] if attendances else default_value)

        return (attendance_from, attendance_to)
