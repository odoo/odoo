# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (c) 2005-2006 Axelor SARL. (http://www.axelor.com)

import logging

from datetime import datetime, time
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.addons.resource.models.resource import HOURS_PER_DAY
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.translate import _
from odoo.tools.float_utils import float_round
from odoo.osv import expression

_logger = logging.getLogger(__name__)


class HolidaysAllocation(models.Model):
    """ Allocation Requests Access specifications: similar to leave requests """
    _name = "hr.leave.allocation"
    _description = "Time Off Allocation"
    _order = "create_date desc"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _mail_post_access = 'read'

    def _default_holiday_status_id(self):
        if self.user_has_groups('hr_holidays.group_hr_holidays_user'):
            domain = [('valid', '=', True)]
        else:
            domain = [('valid', '=', True), ('allocation_type', '=', 'fixed_allocation')]
        return self.env['hr.leave.type'].search(domain, limit=1)

    def _holiday_status_id_domain(self):
        if self.user_has_groups('hr_holidays.group_hr_holidays_manager'):
            return [('valid', '=', True), ('allocation_type', '!=', 'no')]
        return [('valid', '=', True), ('allocation_type', '=', 'fixed_allocation')]

    name = fields.Char('Description', compute='_compute_description', inverse='_inverse_description', search='_search_description', compute_sudo=False)
    private_name = fields.Char('Allocation Description', groups='hr_holidays.group_hr_holidays_user')
    state = fields.Selection([
        ('draft', 'To Submit'),
        ('cancel', 'Cancelled'),
        ('confirm', 'To Approve'),
        ('refuse', 'Refused'),
        ('validate1', 'Second Approval'),
        ('validate', 'Approved')
        ], string='Status', readonly=True, tracking=True, copy=False, default='confirm',
        help="The status is set to 'To Submit', when an allocation request is created." +
        "\nThe status is 'To Approve', when an allocation request is confirmed by user." +
        "\nThe status is 'Refused', when an allocation request is refused by manager." +
        "\nThe status is 'Approved', when an allocation request is approved by manager.")
    date_from = fields.Datetime(
        'Start Date', readonly=True, index=True, copy=False, default=fields.Date.context_today,
        states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]}, tracking=True)
    date_to = fields.Datetime(
        'End Date', compute='_compute_from_holiday_status_id', store=True, readonly=False, copy=False, tracking=True,
        states={'cancel': [('readonly', True)], 'refuse': [('readonly', True)], 'validate1': [('readonly', True)], 'validate': [('readonly', True)]})
    holiday_status_id = fields.Many2one(
        "hr.leave.type", compute='_compute_from_employee_id', store=True, string="Time Off Type", required=True, readonly=False,
        states={'cancel': [('readonly', True)], 'refuse': [('readonly', True)], 'validate1': [('readonly', True)], 'validate': [('readonly', True)]},
        domain=_holiday_status_id_domain)
    employee_id = fields.Many2one(
        'hr.employee', compute='_compute_from_holiday_type', store=True, string='Employee', index=True, readonly=False, ondelete="restrict", tracking=True,
        states={'cancel': [('readonly', True)], 'refuse': [('readonly', True)], 'validate1': [('readonly', True)], 'validate': [('readonly', True)]})
    manager_id = fields.Many2one('hr.employee', compute='_compute_from_employee_id', store=True, string='Manager')
    notes = fields.Text('Reasons', readonly=True, states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    # duration
    number_of_days = fields.Float(
        'Number of Days', compute='_compute_from_holiday_status_id', store=True, readonly=False, tracking=True, default=1,
        help='Duration in days. Reference field to use when necessary.')
    number_of_days_display = fields.Float(
        'Duration (days)', compute='_compute_number_of_days_display',
        states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]},
        help="If Accrual Allocation: Number of days allocated in addition to the ones you will get via the accrual' system.")
    number_of_hours_display = fields.Float(
        'Duration (hours)', compute='_compute_number_of_hours_display',
        help="If Accrual Allocation: Number of hours allocated in addition to the ones you will get via the accrual' system.")
    duration_display = fields.Char('Allocated (Days/Hours)', compute='_compute_duration_display',
        help="Field allowing to see the allocation duration in days or hours depending on the type_request_unit")
    # details
    parent_id = fields.Many2one('hr.leave.allocation', string='Parent')
    linked_request_ids = fields.One2many('hr.leave.allocation', 'parent_id', string='Linked Requests')
    first_approver_id = fields.Many2one(
        'hr.employee', string='First Approval', readonly=True, copy=False,
        help='This area is automatically filled by the user who validates the allocation')
    second_approver_id = fields.Many2one(
        'hr.employee', string='Second Approval', readonly=True, copy=False,
        help='This area is automaticly filled by the user who validates the allocation with second level (If allocation type need second validation)')
    validation_type = fields.Selection(string='Validation Type', related='holiday_status_id.allocation_validation_type', readonly=True)
    can_reset = fields.Boolean('Can reset', compute='_compute_can_reset')
    can_approve = fields.Boolean('Can Approve', compute='_compute_can_approve')
    type_request_unit = fields.Selection(related='holiday_status_id.request_unit', readonly=True)
    # mode
    holiday_type = fields.Selection([
        ('employee', 'By Employee'),
        ('company', 'By Company'),
        ('department', 'By Department'),
        ('category', 'By Employee Tag')],
        string='Allocation Mode', readonly=True, required=True, default='employee',
        states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]},
        help="Allow to create requests in batchs:\n- By Employee: for a specific employee"
             "\n- By Company: all employees of the specified company"
             "\n- By Department: all employees of the specified department"
             "\n- By Employee Tag: all employees of the specific employee group category")
    mode_company_id = fields.Many2one(
        'res.company', compute='_compute_from_holiday_type', store=True, string='Company Mode', readonly=False,
        states={'cancel': [('readonly', True)], 'refuse': [('readonly', True)], 'validate1': [('readonly', True)], 'validate': [('readonly', True)]})
    department_id = fields.Many2one(
        'hr.department', compute='_compute_department_id', store=True, string='Department',
        states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    category_id = fields.Many2one(
        'hr.employee.category', compute='_compute_from_holiday_type', store=True, string='Employee Tag', readonly=False,
        states={'cancel': [('readonly', True)], 'refuse': [('readonly', True)], 'validate1': [('readonly', True)], 'validate': [('readonly', True)]})
    # accrual configuration
    allocation_type = fields.Selection(
        [
            ('regular', 'Regular Allocation'),
            ('accrual', 'Accrual Allocation')
        ], string="Allocation Type", default="regular", required=True, readonly=True,
        states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    accrual_limit = fields.Integer('Balance limit', default=0, help="Maximum of allocation for accrual; 0 means no maximum.")
    number_per_interval = fields.Float("Number of unit per interval", compute='_compute_from_holiday_status_id', store=True, readonly=False,
        states={'cancel': [('readonly', True)], 'refuse': [('readonly', True)], 'validate1': [('readonly', True)], 'validate': [('readonly', True)]})
    interval_number = fields.Integer("Number of unit between two intervals", compute='_compute_from_holiday_status_id', store=True, readonly=False,
        states={'cancel': [('readonly', True)], 'refuse': [('readonly', True)], 'validate1': [('readonly', True)], 'validate': [('readonly', True)]})
    unit_per_interval = fields.Selection([
        ('hours', 'Hours'),
        ('days', 'Days')
        ], compute='_compute_from_holiday_status_id', store=True, string="Unit of time added at each interval", readonly=False,
        states={'cancel': [('readonly', True)], 'refuse': [('readonly', True)], 'validate1': [('readonly', True)], 'validate': [('readonly', True)]})
    interval_unit = fields.Selection([
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months'),
        ('years', 'Years')
        ], compute='_compute_from_holiday_status_id', store=True, string="Unit of time between two intervals", readonly=False,
        states={'cancel': [('readonly', True)], 'refuse': [('readonly', True)], 'validate1': [('readonly', True)], 'validate': [('readonly', True)]})
    nextcall = fields.Date("Date of the next accrual allocation", default=False, readonly=True)
    max_leaves = fields.Float(compute='_compute_leaves')
    leaves_taken = fields.Float(compute='_compute_leaves')

    _sql_constraints = [
        ('type_value',
         "CHECK( (holiday_type='employee' AND employee_id IS NOT NULL) or "
         "(holiday_type='category' AND category_id IS NOT NULL) or "
         "(holiday_type='department' AND department_id IS NOT NULL) or "
         "(holiday_type='company' AND mode_company_id IS NOT NULL))",
         "The employee, department, company or employee category of this request is missing. Please make sure that your user login is linked to an employee."),
        ('duration_check', "CHECK ( number_of_days >= 0 )", "The number of days must be greater than 0."),
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

        holidays = self.search([('allocation_type', '=', 'accrual'), ('employee_id.active', '=', True), ('state', '=', 'validate'), ('holiday_type', '=', 'employee'),
                                '|', ('date_to', '=', False), ('date_to', '>', fields.Datetime.now()),
                                '|', ('nextcall', '=', False), ('nextcall', '<=', today)])

        for holiday in holidays:
            values = {}

            delta = relativedelta(days=0)

            if holiday.interval_unit == 'days':
                delta = relativedelta(days=holiday.interval_number)
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
            start_date = holiday.employee_id._get_date_start_work()
            # If employee is created after the period, we cancel the computation
            if period_end <= start_date or period_end < holiday.date_from:
                holiday.write(values)
                continue

            # If employee created during the period, taking the date at which he has been created
            if period_start <= start_date:
                period_start = start_date

            employee = holiday.employee_id
            worked = employee._get_work_days_data_batch(
                period_start, period_end,
                domain=[('holiday_id.holiday_status_id.unpaid', '=', True), ('time_type', '=', 'leave')]
            )[employee.id]['days']
            left = employee._get_leave_days_data_batch(
                period_start, period_end,
                domain=[('holiday_id.holiday_status_id.unpaid', '=', True), ('time_type', '=', 'leave')]
            )[employee.id]['days']
            prorata = worked / (left + worked) if worked else 0

            days_to_give = holiday.number_per_interval
            if holiday.unit_per_interval == 'hours':
                # As we encode everything in days in the database we need to convert
                # the number of hours into days for this we use the
                # mean number of hours set on the employee's calendar
                days_to_give = days_to_give / (employee.resource_calendar_id.hours_per_day or HOURS_PER_DAY)

            values['number_of_days'] = holiday.number_of_days + days_to_give * prorata
            if holiday.accrual_limit > 0:
                values['number_of_days'] = min(values['number_of_days'], holiday.accrual_limit)

            holiday.write(values)

    @api.depends_context('uid')
    def _compute_description(self):
        self.check_access_rights('read')
        self.check_access_rule('read')

        is_officer = self.env.user.has_group('hr_holidays.group_hr_holidays_user')

        for allocation in self:
            if is_officer or allocation.employee_id.user_id == self.env.user or allocation.manager_id == self.env.user:
                allocation.name = allocation.sudo().private_name
            else:
                allocation.name = '*****'

    def _inverse_description(self):
        is_officer = self.env.user.has_group('hr_holidays.group_hr_holidays_user')
        for allocation in self:
            if is_officer or allocation.employee_id.user_id == self.env.user or allocation.manager_id == self.env.user:
                allocation.sudo().private_name = allocation.name

    def _search_description(self, operator, value):
        is_officer = self.env.user.has_group('hr_holidays.group_hr_holidays_user')
        domain = [('private_name', operator, value)]

        if not is_officer:
            domain = expression.AND([domain, [('employee_id.user_id', '=', self.env.user.id)]])

        allocations = self.sudo().search(domain)
        return [('id', 'in', allocations.ids)]

    @api.depends('employee_id', 'holiday_status_id')
    def _compute_leaves(self):
        for allocation in self:
            leave_type = allocation.holiday_status_id.with_context(employee_id=allocation.employee_id.id)
            allocation.max_leaves = leave_type.max_leaves
            allocation.leaves_taken = leave_type.leaves_taken

    @api.depends('number_of_days')
    def _compute_number_of_days_display(self):
        for allocation in self:
            allocation.number_of_days_display = allocation.number_of_days

    @api.depends('number_of_days', 'employee_id')
    def _compute_number_of_hours_display(self):
        for allocation in self:
            if allocation.parent_id and allocation.parent_id.type_request_unit == "hour":
                allocation.number_of_hours_display = allocation.number_of_days * HOURS_PER_DAY
            elif allocation.number_of_days:
                allocation.number_of_hours_display = allocation.number_of_days * (allocation.employee_id.sudo().resource_id.calendar_id.hours_per_day or HOURS_PER_DAY)
            else:
                allocation.number_of_hours_display = 0.0

    @api.depends('number_of_hours_display', 'number_of_days_display')
    def _compute_duration_display(self):
        for allocation in self:
            allocation.duration_display = '%g %s' % (
                (float_round(allocation.number_of_hours_display, precision_digits=2)
                if allocation.type_request_unit == 'hour'
                else float_round(allocation.number_of_days_display, precision_digits=2)),
                _('hours') if allocation.type_request_unit == 'hour' else _('days'))

    @api.depends('state', 'employee_id', 'department_id')
    def _compute_can_reset(self):
        for allocation in self:
            try:
                allocation._check_approval_update('draft')
            except (AccessError, UserError):
                allocation.can_reset = False
            else:
                allocation.can_reset = True

    @api.depends('state', 'employee_id', 'department_id')
    def _compute_can_approve(self):
        for allocation in self:
            try:
                if allocation.state == 'confirm' and allocation.validation_type == 'both':
                    allocation._check_approval_update('validate1')
                else:
                    allocation._check_approval_update('validate')
            except (AccessError, UserError):
                allocation.can_approve = False
            else:
                allocation.can_approve = True

    @api.depends('holiday_type')
    def _compute_from_holiday_type(self):
        for allocation in self:
            if allocation.holiday_type == 'employee':
                if not allocation.employee_id:
                    allocation.employee_id = self.env.user.employee_id
                allocation.mode_company_id = False
                allocation.category_id = False
            if allocation.holiday_type == 'company':
                allocation.employee_id = False
                if not allocation.mode_company_id:
                    allocation.mode_company_id = self.env.company
                allocation.category_id = False
            elif allocation.holiday_type == 'department':
                allocation.employee_id = False
                allocation.mode_company_id = False
                allocation.category_id = False
            elif allocation.holiday_type == 'category':
                allocation.employee_id = False
                allocation.mode_company_id = False
            elif not allocation.employee_id and not allocation._origin.employee_id:
                allocation.employee_id = self.env.context.get('default_employee_id') or self.env.user.employee_id

    @api.depends('holiday_type', 'employee_id')
    def _compute_department_id(self):
        for allocation in self:
            if allocation.holiday_type == 'employee':
                allocation.department_id = allocation.employee_id.department_id
            elif allocation.holiday_type == 'department':
                if not allocation.department_id:
                    allocation.department_id = self.env.user.employee_id.department_id
            elif allocation.holiday_type == 'category':
                allocation.department_id = False

    @api.depends('employee_id')
    def _compute_from_employee_id(self):
        default_holiday_status_id = self._default_holiday_status_id()
        for holiday in self:
            holiday.manager_id = holiday.employee_id and holiday.employee_id.parent_id
            if holiday.employee_id.user_id != self.env.user and holiday._origin.employee_id != holiday.employee_id:
                holiday.holiday_status_id = False
            elif not holiday.holiday_status_id and not holiday._origin.holiday_status_id:
                holiday.holiday_status_id = default_holiday_status_id

    @api.depends('holiday_status_id', 'allocation_type', 'number_of_hours_display', 'number_of_days_display')
    def _compute_from_holiday_status_id(self):
        for allocation in self:
            allocation.number_of_days = allocation.number_of_days_display
            if allocation.type_request_unit == 'hour':
                allocation.number_of_days = allocation.number_of_hours_display / (allocation.employee_id.sudo().resource_calendar_id.hours_per_day or HOURS_PER_DAY)

            # set default values
            if not allocation.interval_number and not allocation._origin.interval_number:
                allocation.interval_number = 1
            if not allocation.number_per_interval and not allocation._origin.number_per_interval:
                allocation.number_per_interval = 1
            if not allocation.unit_per_interval and not allocation._origin.unit_per_interval:
                allocation.unit_per_interval = 'hours'
            if not allocation.interval_unit and not allocation._origin.interval_unit:
                allocation.interval_unit = 'weeks'

            if allocation.holiday_status_id.validity_stop and allocation.date_to:
                new_date_to = datetime.combine(allocation.holiday_status_id.validity_stop, time.max)
                if new_date_to < allocation.date_to:
                    allocation.date_to = new_date_to

            if allocation.allocation_type == 'accrual':
                if allocation.holiday_status_id.request_unit == 'hour':
                    allocation.unit_per_interval = 'hours'
                else:
                    allocation.unit_per_interval = 'days'
            else:
                allocation.interval_number = 1
                allocation.interval_unit = 'weeks'
                allocation.number_per_interval = 1
                allocation.unit_per_interval = 'hours'

    ####################################################
    # ORM Overrides methods
    ####################################################

    def name_get(self):
        res = []
        for allocation in self:
            if allocation.holiday_type == 'company':
                target = allocation.mode_company_id.name
            elif allocation.holiday_type == 'department':
                target = allocation.department_id.name
            elif allocation.holiday_type == 'category':
                target = allocation.category_id.name
            else:
                target = allocation.employee_id.sudo().name

            res.append(
                (allocation.id,
                 _("Allocation of %(allocation_name)s : %(duration).2f %(duration_type)s to %(person)s",
                   allocation_name=allocation.holiday_status_id.sudo().name,
                   duration=allocation.number_of_hours_display if allocation.type_request_unit == 'hour' else allocation.number_of_days,
                   duration_type='hours' if allocation.type_request_unit == 'hour' else 'days',
                   person=target
                ))
            )
        return res

    def add_follower(self, employee_id):
        employee = self.env['hr.employee'].browse(employee_id)
        if employee.user_id:
            self.message_subscribe(partner_ids=employee.user_id.partner_id.ids)

    @api.constrains('holiday_status_id')
    def _check_leave_type_validity(self):
        for allocation in self:
            if allocation.holiday_status_id.validity_stop:
                vstop = allocation.holiday_status_id.validity_stop
                today = fields.Date.today()

                if vstop < today:
                    raise ValidationError(_(
                        'You can allocate %(allocation_type)s only before %(date)s.',
                        allocation_type=allocation.holiday_status_id.display_name,
                        date=allocation.holiday_status_id.validity_stop
                    ))

    @api.model
    def create(self, values):
        """ Override to avoid automatic logging of creation """
        employee_id = values.get('employee_id', False)
        if not values.get('department_id'):
            values.update({'department_id': self.env['hr.employee'].browse(employee_id).department_id.id})
        holiday = super(HolidaysAllocation, self.with_context(mail_create_nosubscribe=True)).create(values)
        holiday.add_follower(employee_id)
        if holiday.validation_type == 'hr':
            holiday.message_subscribe(partner_ids=(holiday.employee_id.parent_id.user_id.partner_id | holiday.employee_id.leave_manager_id.partner_id).ids)
        if not self._context.get('import_file'):
            holiday.activity_update()
        return holiday

    def write(self, values):
        employee_id = values.get('employee_id', False)
        if values.get('state'):
            self._check_approval_update(values['state'])
        result = super(HolidaysAllocation, self).write(values)
        self.add_follower(employee_id)
        return result

    def unlink(self):
        state_description_values = {elem[0]: elem[1] for elem in self._fields['state']._description_selection(self.env)}
        for holiday in self.filtered(lambda holiday: holiday.state not in ['draft', 'cancel', 'confirm']):
            raise UserError(_('You cannot delete an allocation request which is in %s state.') % (state_description_values.get(holiday.state),))
        return super(HolidaysAllocation, self).unlink()

    def _get_mail_redirect_suggested_company(self):
        return self.holiday_status_id.company_id

    ####################################################
    # Business methods
    ####################################################

    def _prepare_holiday_values(self, employee):
        self.ensure_one()
        values = {
            'name': self.name,
            'holiday_type': 'employee',
            'holiday_status_id': self.holiday_status_id.id,
            'notes': self.notes,
            'number_of_days': self.number_of_days,
            'parent_id': self.id,
            'employee_id': employee.id,
            'allocation_type': self.allocation_type,
            'date_from': self.date_from,
            'date_to': self.date_to,
            'interval_unit': self.interval_unit,
            'interval_number': self.interval_number,
            'number_per_interval': self.number_per_interval,
            'unit_per_interval': self.unit_per_interval,
        }
        return values

    def action_draft(self):
        if any(holiday.state not in ['confirm', 'refuse'] for holiday in self):
            raise UserError(_('Allocation request state must be "Refused" or "To Approve" in order to reset to Draft.'))
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
            raise UserError(_('Allocation request must be in Draft state ("To Submit") in order to confirm it.'))
        res = self.write({'state': 'confirm'})
        self.activity_update()
        return res

    def action_approve(self):
        # if validation_type == 'both': this method is the first approval approval
        # if validation_type != 'both': this method calls action_validate() below
        if any(holiday.state != 'confirm' for holiday in self):
            raise UserError(_('Allocation request must be confirmed ("To Approve") in order to approve it.'))

        current_employee = self.env.user.employee_id

        self.filtered(lambda hol: hol.validation_type == 'both').write({'state': 'validate1', 'first_approver_id': current_employee.id})
        self.filtered(lambda hol: not hol.validation_type == 'both').action_validate()
        self.activity_update()

    def action_validate(self):
        current_employee = self.env.user.employee_id
        for holiday in self:
            if holiday.state not in ['confirm', 'validate1']:
                raise UserError(_('Allocation request must be confirmed in order to approve it.'))

            holiday.write({'state': 'validate'})
            if holiday.validation_type == 'both':
                holiday.write({'second_approver_id': current_employee.id})
            else:
                holiday.write({'first_approver_id': current_employee.id})

            holiday._action_validate_create_childs()
        self.activity_update()
        return True

    def _action_validate_create_childs(self):
        childs = self.env['hr.leave.allocation']
        if self.state == 'validate' and self.holiday_type in ['category', 'department', 'company']:
            if self.holiday_type == 'category':
                employees = self.category_id.employee_ids
            elif self.holiday_type == 'department':
                employees = self.department_id.member_ids
            else:
                employees = self.env['hr.employee'].search([('company_id', '=', self.mode_company_id.id)])

            for employee in employees:
                childs += self.with_context(
                    mail_notify_force_send=False,
                    mail_activity_automation_skip=True
                ).create(self._prepare_holiday_values(employee))
            # TODO is it necessary to interleave the calls?
            childs.action_approve()
            if childs and self.validation_type == 'both':
                childs.action_validate()
        return childs

    def action_refuse(self):
        current_employee = self.env.user.employee_id
        if any(holiday.state not in ['confirm', 'validate', 'validate1'] for holiday in self):
            raise UserError(_('Allocation request must be confirmed or validated in order to refuse it.'))

        validated_holidays = self.filtered(lambda hol: hol.state == 'validate1')
        validated_holidays.write({'state': 'refuse', 'first_approver_id': current_employee.id})
        (self - validated_holidays).write({'state': 'refuse', 'second_approver_id': current_employee.id})
        # If a category that created several holidays, cancel all related
        linked_requests = self.mapped('linked_request_ids')
        if linked_requests:
            linked_requests.action_refuse()
        self.activity_update()
        return True

    def _check_approval_update(self, state):
        """ Check if target state is achievable. """
        if self.env.is_superuser():
            return
        current_employee = self.env.user.employee_id
        if not current_employee:
            return
        is_officer = self.env.user.has_group('hr_holidays.group_hr_holidays_user')
        is_manager = self.env.user.has_group('hr_holidays.group_hr_holidays_manager')
        for holiday in self:
            val_type = holiday.holiday_status_id.sudo().allocation_validation_type
            if state == 'confirm':
                continue

            if state == 'draft':
                if holiday.employee_id != current_employee and not is_manager:
                    raise UserError(_('Only a time off Manager can reset other people allocation.'))
                continue

            if not is_officer and self.env.user != holiday.employee_id.leave_manager_id:
                raise UserError(_('Only a time off Officer/Responsible or Manager can approve or refuse time off requests.'))

            if is_officer or self.env.user == holiday.employee_id.leave_manager_id:
                # use ir.rule based first access check: department, members, ... (see security.xml)
                holiday.check_access_rule('write')

            if holiday.employee_id == current_employee and not is_manager:
                raise UserError(_('Only a time off Manager can approve its own requests.'))

            if (state == 'validate1' and val_type == 'both') or (state == 'validate' and val_type == 'manager'):
                if self.env.user == holiday.employee_id.leave_manager_id and self.env.user != holiday.employee_id.user_id:
                    continue
                manager = holiday.employee_id.parent_id or holiday.employee_id.department_id.manager_id
                if (manager != current_employee) and not is_manager:
                    raise UserError(_('You must be either %s\'s manager or time off manager to approve this time off') % (holiday.employee_id.name))

            if state == 'validate' and val_type == 'both':
                if not is_officer:
                    raise UserError(_('Only a Time off Approver can apply the second approval on allocation requests.'))

    # ------------------------------------------------------------
    # Activity methods
    # ------------------------------------------------------------

    def _get_responsible_for_approval(self):
        self.ensure_one()
        responsible = self.env.user

        if self.validation_type == 'manager' or (self.validation_type == 'both' and self.state == 'confirm'):
            if self.employee_id.leave_manager_id:
                responsible = self.employee_id.leave_manager_id
        elif self.validation_type == 'hr' or (self.validation_type == 'both' and self.state == 'validate1'):
            if self.holiday_status_id.responsible_id:
                responsible = self.holiday_status_id.responsible_id

        return responsible

    def activity_update(self):
        to_clean, to_do = self.env['hr.leave.allocation'], self.env['hr.leave.allocation']
        for allocation in self:
            note = _(
                'New Allocation Request created by %(user)s: %(count)s Days of %(allocation_type)s',
                user=allocation.create_uid.name,
                count=allocation.number_of_days,
                allocation_type=allocation.holiday_status_id.name
            )
            if allocation.state == 'draft':
                to_clean |= allocation
            elif allocation.state == 'confirm':
                allocation.activity_schedule(
                    'hr_holidays.mail_act_leave_allocation_approval',
                    note=note,
                    user_id=allocation.sudo()._get_responsible_for_approval().id or self.env.user.id)
            elif allocation.state == 'validate1':
                allocation.activity_feedback(['hr_holidays.mail_act_leave_allocation_approval'])
                allocation.activity_schedule(
                    'hr_holidays.mail_act_leave_allocation_second_approval',
                    note=note,
                    user_id=allocation.sudo()._get_responsible_for_approval().id or self.env.user.id)
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

    def _track_subtype(self, init_values):
        if 'state' in init_values and self.state == 'validate':
            allocation_notif_subtype_id = self.holiday_status_id.allocation_notif_subtype_id
            return allocation_notif_subtype_id or self.env.ref('hr_holidays.mt_leave_allocation')
        return super(HolidaysAllocation, self)._track_subtype(init_values)

    def _notify_get_groups(self):
        """ Handle HR users and officers recipients that can validate or refuse holidays
        directly from email. """
        groups = super(HolidaysAllocation, self)._notify_get_groups()

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

    def message_subscribe(self, partner_ids=None, channel_ids=None, subtype_ids=None):
        # due to record rule can not allow to add follower and mention on validated leave so subscribe through sudo
        if self.state in ['validate', 'validate1']:
            self.check_access_rights('read')
            self.check_access_rule('read')
            return super(HolidaysAllocation, self.sudo()).message_subscribe(partner_ids=partner_ids, channel_ids=channel_ids, subtype_ids=subtype_ids)
        return super(HolidaysAllocation, self).message_subscribe(partner_ids=partner_ids, channel_ids=channel_ids, subtype_ids=subtype_ids)
