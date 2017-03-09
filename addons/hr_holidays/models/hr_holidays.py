# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (c) 2005-2006 Axelor SARL. (http://www.axelor.com)

import logging
import math
from datetime import datetime, timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)


HOURS_PER_DAY = 8


class HolidaysType(models.Model):
    _name = "hr.holidays.status"
    _description = "Leave Type"

    name = fields.Char('Leave Type', required=True, translate=True)
    categ_id = fields.Many2one('calendar.event.type', string='Show in Meeting',
        help='Once a leave is validated, Odoo will create a corresponding meeting of this type in the calendar.')
    color_name = fields.Selection([
        ('red', 'Red'),
        ('blue', 'Blue'),
        ('lightgreen', 'Light Green'),
        ('lightblue', 'Light Blue'),
        ('lightyellow', 'Light Yellow'),
        ('magenta', 'Magenta'),
        ('lightcyan', 'Light Cyan'),
        ('black', 'Black'),
        ('lightpink', 'Light Pink'),
        ('brown', 'Brown'),
        ('violet', 'Violet'),
        ('lightcoral', 'Light Coral'),
        ('lightsalmon', 'Light Salmon'),
        ('lavender', 'Lavender'),
        ('wheat', 'Wheat'),
        ('ivory', 'Ivory')], string='Color in Report', required=True, default='red',
        help='This color will be used in the leaves summary located in Reporting > Leaves by Department.')
    limit = fields.Boolean('Allow to Override Limit',
        help='If you select this check box, the system allows the employees to take more leaves '
             'than the available ones for this type and will not take them into account for the '
             '"Remaining Legal Leaves" defined on the employee form.')

    active = fields.Boolean('Active', default=True,
        help="If the active field isn't checked, it will allow you to hide the leave type without removing it.")
    max_leaves = fields.Float(compute='_compute_leaves', string='Maximum Allowed',
        help="This value is given by the sum of all leave allocations that haven't expired yet.")
    leaves_taken = fields.Float(compute='_compute_leaves', string='Leaves Already Taken',
        help="Depending on the leave type, it's the number of leaves taken this year if from a limitless type"
             " or leaves taken from those that you would currently still have at this date if not taken.")
    remaining_leaves = fields.Float(compute='_compute_leaves', string='Remaining Leaves',
        help='Maximum Leaves Allowed - Leaves Already Taken')
    virtual_remaining_leaves = fields.Float(compute='_compute_leaves', string='Virtual Remaining Leaves',
        help='Maximum Leaves Allowed - Leaves Already Taken - Leaves Waiting Approval') # can I remove one of these fields and keep the virtual_ meaning ? it's unused except for in 1 test.
    next_expiration_date = fields.Date('Next Leave Expiration Date', compute='_compute_next_expiration')
    next_expiration_amount = fields.Float('Next Leave Expiration Amount', compute='_compute_next_expiration')

    double_validation = fields.Boolean(string='Apply Double Validation',
        help="When selected, the Allocation/Leave Requests for this type require a second validation to be approved.")
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id)

    @api.multi
    def get_days(self, employee_id):
        # need to use `dict` constructor to create a dict per id
        result = dict((id, dict(max_leaves=0, leaves_taken=0, remaining_leaves=0, virtual_remaining_leaves=0)) for id in self.ids)

        holidays = self.env['hr.holidays'].search([
            ('employee_id', '=', employee_id),
            ('state', '=', 'validate'),
            ('holiday_status_id', 'in', self.ids),
            '|', ('type', '=', 'add'),
                 '&', ('type', '=', 'remove'),
                      '&', ('holiday_status_id', 'in', self.filtered('limit').ids),
                           ('date_from', '>', fields.Date.to_string(datetime.now().replace(month=1, day=1))),
        ])
        for holiday in holidays:
            status_dict = result[holiday.holiday_status_id.id]
            if holiday.type == 'add':
                status_dict['max_leaves'] += holiday.number_of_days_temp
                status_dict['leaves_taken'] += holiday.number_of_days_temp - holiday.remaining_leave_days
                if not holiday.expiration_date or holiday.expiration_date >= fields.Date.today():
                    status_dict['virtual_remaining_leaves'] += holiday.virtual_remaining_leave_days
                    status_dict['remaining_leaves'] += holiday.remaining_leave_days
            else:
                status_dict['leaves_taken'] += holiday.number_of_days_temp

        return result

    @api.multi
    def _compute_leaves(self):
        data_days = {}
        if 'employee_id' in self._context:
            employee_id = self._context['employee_id']
        else:
            employee_id = self.env['hr.employee'].search([('user_id', '=', self.env.user.id)], limit=1).id

        if employee_id:
            data_days = self.get_days(employee_id)

        for holiday_status in self:
            result = data_days.get(holiday_status.id, {})
            holiday_status.max_leaves = result.get('max_leaves', 0)
            holiday_status.leaves_taken = result.get('leaves_taken', 0)
            holiday_status.remaining_leaves = result.get('remaining_leaves', 0)
            holiday_status.virtual_remaining_leaves = result.get('virtual_remaining_leaves', 0)

    def _compute_next_expiration(self):
        if 'employee_id' in self._context:
            employee_id = self._context['employee_id']
        else:
            employee_id = self.env['hr.employee'].search([('user_id', '=', self.env.user.id)], limit=1).id

        if employee_id:
            limited_holiday_status = self.filtered(lambda s: not s.limit)
            expiration_allocations = self.env['hr.holidays'].search([
                ('employee_id', '=', employee_id),
                ('type', '=', 'add'),
                ('state', '=', 'validate'),
                ('holiday_status_id', 'in', limited_holiday_status.ids),
                ('expiration_date', '>=', fields.Date.today())], order='expiration_date')
            for status in limited_holiday_status:
                next_expiration_allocations = expiration_allocations.filtered(lambda alloc: alloc.holiday_status_id.id == status.id and alloc.virtual_remaining_leave_days > 0)
                if next_expiration_allocations:
                    status.next_expiration_date = next_expiration_allocations[0].expiration_date
                    status.next_expiration_amount = next_expiration_allocations[0].virtual_remaining_leave_days

    @api.multi
    def name_get(self):
        if not self._context.get('employee_id'):
            # leave counts is based on employee_id, would be inaccurate if not based on correct employee
            return super(HolidaysType, self).name_get()
        res = []
        for record in self:
            name = record.name
            if not record.limit:
                name = "%(name)s (%(count)s)" % {
                    'name': name,
                    'count': _('%g remaining out of %g') % (record.virtual_remaining_leaves or 0.0, record.max_leaves or 0.0)
                }
            res.append((record.id, name))
        return res

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        """ Override _search to order the results, according to some employee.
        The order is the following

         - limit (limited leaves first, such as Legal Leaves)
         - virtual remaining leaves (higher the better, so using reverse on sorted)

        This override is necessary because those fields are not stored and depends
        on an employee_id given in context. This sort will be done when there
        is an employee_id in context and that no other order has been given
        to the method.
        """
        leave_ids = super(HolidaysType, self)._search(args, offset=offset, limit=limit, order=order, count=count, access_rights_uid=access_rights_uid)
        if not count and not order and self._context.get('employee_id'):
            leaves = self.browse(leave_ids)
            sort_key = lambda l: (not l.limit, l.virtual_remaining_leaves)
            return leaves.sorted(key=sort_key, reverse=True).ids
        return leave_ids


class Holidays(models.Model):
    _name = "hr.holidays"
    _description = "Leave"
    _order = "type desc, date_from desc"
    _inherit = ['mail.thread']

    def _default_employee(self):
        return self.env.context.get('default_employee_id') or self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)

    def _default_date_from(self):
        if self.env.context.get('default_type') == 'add':
            return False
        employee_id = self.env.context.get('default_employee_id')
        employee = self.env['hr.employee'].browse(employee_id) or self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
        if not employee:
            return False
        return employee.get_start_work_hour(datetime.now())

    def _default_date_to(self):
        if self.env.context.get('default_type') == 'add':
            return False
        employee_id = self.env.context.get('default_employee_id')
        employee = self.env['hr.employee'].browse(employee_id) or self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
        if not employee:
            return False
        return employee.get_end_work_hour(datetime.now())

    name = fields.Char('Description')
    state = fields.Selection([
        ('draft', 'To Submit'),
        ('confirm', 'To Approve'),
        ('refuse', 'Refused'),
        ('validate1', 'Second Approval'),
        ('validate', 'Approved')
        ], string='Status', readonly=True, track_visibility='onchange', copy=False, default='draft',
            help="The status is set to 'To Submit', when a leave request is created." +
            "\nThe status is 'To Approve', when leave request is confirmed by user." +
            "\nThe status is 'Refused', when leave request is refused by manager." +
            "\nThe status is 'Approved', when leave request is approved by manager.")
    payslip_status = fields.Boolean('Reported in last payslips',
        help='Green this button when the leave has been taken into account in the payslip.')
    report_note = fields.Text('HR Comments')
    user_id = fields.Many2one('res.users', string='User', related='employee_id.user_id', related_sudo=True, store=True, readonly=True)
    date_from = fields.Datetime('Start Date', default=_default_date_from, readonly=True, index=True, copy=False,
        states={'draft': [('readonly', False)]}, track_visibility='onchange')
    date_to = fields.Datetime('End Date', default=_default_date_to, readonly=True, copy=False,
        states={'draft': [('readonly', False)]}, track_visibility='onchange')
    holiday_status_id = fields.Many2one(
        "hr.holidays.status", string="Leave Type", required=True, readonly=True,
        states={'draft': [('readonly', False)]})
    employee_id = fields.Many2one('hr.employee', string='Employee', index=True, readonly=True,
        states={'draft': [('readonly', False)]}, default=_default_employee, track_visibility='onchange')
    manager_id = fields.Many2one('hr.employee', related='employee_id.parent_id', string='Manager', readonly=True, store=True)
    notes = fields.Text('Reasons', readonly=True, states={'draft': [('readonly', False)]})
    number_of_days_temp = fields.Float(
        'Day(s)', copy=False, readonly=True,
        states={'draft': [('readonly', False)]},
        help='Number of days of the leave request according to your working schedule.')
    number_of_days = fields.Float('Number of Days', compute='_compute_number_of_days', store=True, track_visibility='onchange')
    meeting_id = fields.Many2one('calendar.event', string='Meeting')
    type = fields.Selection([
            ('remove', 'Leave Request'),
            ('add', 'Allocation Request')
        ], string='Request Type', required=True, readonly=True, index=True, track_visibility='always', default='remove',
        states={'draft': [('readonly', False)]},
        help="Choose 'Leave Request' if someone wants to take an off-day. "
             "\nChoose 'Allocation Request' if you want to increase the number of leaves available for someone")
    parent_id = fields.Many2one('hr.holidays', string='Parent')
    linked_request_ids = fields.One2many('hr.holidays', 'parent_id', string='Linked Requests')
    department_id = fields.Many2one(
        'hr.department', string='Department', readonly=True,
        states={'draft': [('readonly', False)]})
    category_id = fields.Many2one('hr.employee.category', string='Employee Tag', readonly=True,
        states={'draft': [('readonly', False)]}, help='Category of Employee')
    holiday_type = fields.Selection([
        ('employee', 'By Employee'),
        ('department', 'By Department'),
        ('category', 'By Employee Tag'),
    ], string='Allocation Mode', readonly=True, required=True, default='employee',
        states={'draft': [('readonly', False)]},
        help='By Employee: Allocation/Request for individual Employee, By Employee Tag: Allocation/Request for group of employees in category')
    first_approver_id = fields.Many2one('hr.employee', string='First Approval', readonly=True, copy=False,
        help='This area is automatically filled by the user who validate the leave', oldname='manager_id')
    second_approver_id = fields.Many2one('hr.employee', string='Second Approval', readonly=True, copy=False, oldname='manager_id2',
        help='This area is automaticly filled by the user who validate the leave with second level (If Leave type need second validation)')
    double_validation = fields.Boolean('Apply Double Validation', related='holiday_status_id.double_validation')
    can_reset = fields.Boolean('Can reset', compute='_compute_can_reset')
    activation_date = fields.Date(
        'Activation Date', readonly=True, states={'draft': [('readonly', False)]},
        track_visibility='onchange', help="If set, these leaves can only be taken after this date.")
    expiration_date = fields.Date(
        'Expiration Date', readonly=True, states={'draft': [('readonly', False)]},
        track_visibility='onchange', help="If set, these leaves can only be taken before this date.")
    allocation_reservation_ids = fields.One2many('hr.holidays.reservation', 'allocation_id', readonly=True)
    leave_reservation_ids = fields.One2many('hr.holidays.reservation', 'leave_id', readonly=True)
    remaining_leave_days = fields.Float(
        'remaining leaves', compute='_compute_remaining_leave_days', readonly=True,
        help='Remaining leaves for this allocation excluding leaves waiting for approval')
    virtual_remaining_leave_days = fields.Float(
        'virtual remaining leaves', compute='_compute_virtual_remaining_leave_days', readonly=True,
        help='Remaining leaves for this allocation including leaves waiting for approval')

    @api.multi
    @api.depends('number_of_days_temp', 'type')
    def _compute_number_of_days(self):
        for holiday in self:
            if holiday.type == 'remove':
                holiday.number_of_days = -holiday.number_of_days_temp
            else:
                holiday.number_of_days = holiday.number_of_days_temp

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

    def _compute_remaining_leave_days(self):
        allocations = self.filtered(lambda l: l.type == 'add')
        reservation_data = self.env['hr.holidays.reservation'].read_group(
            domain=[('allocation_id', 'in', allocations.ids),
                    ('leave_id.state', '=', 'validate')],
            fields=['days_reserved', 'allocation_id'], groupby=['allocation_id'])
        reserved_days = dict((d['allocation_id'][0], d['days_reserved']) for d in reservation_data)
        for alloc in allocations:
            alloc.remaining_leave_days = alloc.number_of_days - reserved_days.get(alloc.id, 0)

    def _compute_virtual_remaining_leave_days(self):
        allocations = self.filtered(lambda l: l.type == 'add')
        reservation_data = self.env['hr.holidays.reservation'].read_group(
            domain=[('allocation_id', 'in', allocations.ids)],
            fields=['days_reserved', 'allocation_id'], groupby=['allocation_id'])
        reserved_days = dict((d['allocation_id'][0], d['days_reserved']) for d in reservation_data)
        for alloc in allocations:
            alloc.virtual_remaining_leave_days = alloc.number_of_days - reserved_days.get(alloc.id, 0)

    @api.constrains('date_from', 'date_to')
    def _check_date(self):
        for holiday in self.filtered(lambda h: h.type == 'remove'):
            domain = [
                ('date_from', '<=', holiday.date_to),
                ('date_to', '>=', holiday.date_from),
                ('employee_id', '=', holiday.employee_id.id),
                ('type', '=', 'remove'),
                ('id', '!=', holiday.id),
                ('type', '=', holiday.type),
                ('state', 'not in', ['refuse', 'draft']),
            ]
            nholidays = self.search_count(domain)
            if nholidays:
                raise ValidationError(_('You can not have 2 leaves that overlaps on same day!'))

    _sql_constraints = [
        ('type_value', "CHECK( (holiday_type='employee' AND employee_id IS NOT NULL) or (holiday_type='category' AND category_id IS NOT NULL) "
                       " or (holiday_type='department' AND department_id IS NOT NULL))",
         "The employee, employee category or department of this request is missing. Please make sure that your user is linked to an employee."),
        ('date_check2', "CHECK ( (type='add') OR (date_from <= date_to))", "The start date must be anterior to the end date."),
        ('date_check', "CHECK ( number_of_days_temp >= 0 )", "The number of days must be greater than 0."),
    ]

    @api.onchange('holiday_type')
    def _onchange_type(self):
        if self.holiday_type == 'employee' and not self.employee_id:
            self.employee_id = self.env.user.employee_ids[0]
        elif self.holiday_type == 'department':
            self.employee_id = None
            self.department_id = self.department_id or self.env.user.employee_ids[0].department_id
        elif self.holiday_type == 'category':
            self.employee_id = None
            self.department_id = None

    @api.onchange('employee_id')
    def _onchange_employee(self):
        if self.holiday_type == 'employee':
            self.department_id = self.employee_id.department_id

    def _get_number_of_days(self, date_from, date_to, employee_id):
        """ Returns a float equal to the timedelta between two dates given as string."""
        from_dt = fields.Datetime.from_string(date_from)
        to_dt = fields.Datetime.from_string(date_to)

        if employee_id:
            employee = self.env['hr.employee'].browse(employee_id)
            return employee.get_work_days_count(from_dt, to_dt)

        time_delta = to_dt - from_dt
        return math.ceil(time_delta.days + float(time_delta.seconds) / 86400)

    @api.onchange('date_from')
    def _onchange_date_from(self):
        """ If there are no date set for date_to, automatically set one 8 hours later than
            the date_from. Also update the number_of_days.
        """
        date_from = self.date_from
        date_to = self.date_to

        if date_from and (not date_to or date_to < date_from):
            if self.employee_id:
                self.date_to = self.employee_id.get_end_work_hour(fields.Date.from_string(date_from))
            else:
                date_to_with_delta = fields.Datetime.from_string(date_from) + timedelta(hours=HOURS_PER_DAY)
                self.date_to = str(date_to_with_delta)

        # Compute and update the number of days
        if (date_to and date_from) and (date_from <= self.date_to):
            self.number_of_days_temp = self._get_number_of_days(date_from, self.date_to, self.employee_id.id)
        else:
            self.number_of_days_temp = 0

    @api.onchange('date_to')
    def _onchange_date_to(self):
        """ Update the number_of_days. """
        date_from = self.date_from
        date_to = self.date_to

        # Compute and update the number of days
        if (date_to and date_from) and (date_from <= date_to):
            self.number_of_days_temp = self._get_number_of_days(date_from, date_to, self.employee_id.id)
        else:
            self.number_of_days_temp = 0

    ####################################################
    # ORM Overrides methods
    ####################################################

    @api.multi
    def name_get(self):
        res = []
        for leave in self:
            if leave.type == 'remove':
                if self.env.context.get('short_name'):
                    res.append((leave.id, _("%s : %.2f day(s)") % (leave.name or leave.holiday_status_id.name, leave.number_of_days_temp)))
                else:
                    res.append((leave.id, _("%s on %s : %.2f day(s)") % (leave.employee_id.name or leave.category_id.name, leave.holiday_status_id.name, leave.number_of_days_temp)))
            else:
                res.append((leave.id, _("Allocation of %s : %.2f day(s) To %s") % (leave.holiday_status_id.name, leave.number_of_days_temp,
                                                                                   leave.employee_id.name or leave.department_id.name or leave.category_id.name)))
        return res

    @api.multi
    def add_follower(self, employee_id):
        employee = self.env['hr.employee'].browse(employee_id)
        if employee.user_id:
            self.message_subscribe_users(user_ids=employee.user_id.ids)

    def copy(self):
        raise UserError(_('Cannot duplicate a leave.'))

    @api.model
    def create(self, values):
        """ Override to avoid automatic logging of creation """
        employee_id = values.get('employee_id', False)
        if not values.get('department_id'):
            values.update({'department_id': self.env['hr.employee'].browse(employee_id).department_id.id})
        holiday = super(Holidays, self.with_context(mail_create_nolog=True, mail_create_nosubscribe=True)).create(values)
        holiday.add_follower(employee_id)
        holiday.action_confirm()
        return holiday

    @api.multi
    def write(self, values):
        employee_id = values.get('employee_id', False)
        result = super(Holidays, self).write(values)
        self.add_follower(employee_id)
        return result

    @api.multi
    def unlink(self):
        for holiday in self.filtered(lambda holiday: holiday.state not in ['draft', 'refuse']):
            raise UserError(_('You cannot delete a leave which is in %s state.') % (holiday.state,))
        return super(Holidays, self).unlink()

    ####################################################
    # Business methods
    ####################################################

    @api.multi
    def _create_resource_leave(self):
        """ This method will create entry in resource calendar leave object at the time of holidays validated """
        for leave in self:
            self.env['resource.calendar.leaves'].create({
                'name': leave.name,
                'date_from': leave.date_from,
                'holiday_id': leave.id,
                'date_to': leave.date_to,
                'resource_id': leave.employee_id.resource_id.id,
                'calendar_id': leave.employee_id.resource_calendar_id.id
            })
        return True

    @api.multi
    def _remove_resource_leave(self):
        """ This method will create entry in resource calendar leave object at the time of holidays cancel/removed """
        return self.env['resource.calendar.leaves'].search([('holiday_id', 'in', self.ids)]).unlink()

    def cancel_leave_reservations(self):
        """ Check there are no linked leave requests (for allocations) and remove the reservations (for leaves)
        """
        if self.mapped('allocation_reservation_ids'):
            raise UserError(_('You cannot refuse or delete an allocation that already has related leaves.'))
        return self.sudo().mapped('leave_reservation_ids').unlink()

    @api.multi
    def action_draft(self):
        for holiday in self:
            if not holiday.can_reset:
                raise UserError(_('Only an HR Manager or the concerned employee can reset to draft.'))
            if holiday.state not in ['confirm', 'refuse']:
                raise UserError(_('Leave request state must be "Refused" or "To Approve" in order to reset to Draft.'))
            # Remove the reservations
            holiday.cancel_leave_reservations()
            holiday.write({
                'state': 'draft',
                'first_approver_id': False,
                'second_approver_id': False,
            })
            linked_requests = holiday.mapped('linked_request_ids')
            for linked_request in linked_requests:
                linked_request.action_draft()
            linked_requests.unlink()
        return True

    @api.multi
    def action_confirm(self):
        self = self.filtered(lambda holiday: holiday.state != 'confirm')
        if self.filtered(lambda holiday: holiday.state != 'draft'):
            raise UserError(_('Leave request must be in Draft state ("To Submit") in order to confirm it.'))

        if self.filtered(lambda l: l.type == 'add' and l.holiday_status_id.limit):
            raise UserError(_('Cannot make allocations for a holiday type without limit.'))

        # make the reservations between leaves and allocations.
        for leave in self.filtered(lambda l: l.type == 'remove' and l.holiday_type == 'employee' and not l.holiday_status_id.limit):
            days_to_take = leave.number_of_days_temp
            for alloc in self.search([
                ('employee_id', '=', leave.employee_id.id),
                ('type', '=', 'add'),
                ('state', '=', 'validate'),
                ('holiday_status_id', '=', leave.holiday_status_id.id),
                '|', ('activation_date', '<=', fields.Date.to_string(fields.Datetime.from_string(leave.date_to).date())),
                     ('activation_date', '=', False),
                '|', ('expiration_date', '>=', fields.Date.to_string(fields.Datetime.from_string(leave.date_from).date())),
                     ('expiration_date', '=', False)
            ], order='expiration_date').filtered(lambda al: al.virtual_remaining_leave_days > 0):

                days_to_reserve = min(days_to_take, alloc.virtual_remaining_leave_days)

                # We make the assumption that at most one allocation can have dates that constrains the leave.
                # To handle it cleanly, we'd need to add a daterange system that would complexify the system a lot.
                # Also, as the current system isn't clean (we can take 10 days of leaves and force it to 5), it can't be done.

                if (alloc.expiration_date and alloc.expiration_date < leave.date_to or
                        alloc.activation_date and alloc.activation_date > leave.date_from):
                    # we reserve the maximum amount of days on the allocation, according to the employee's working calendar
                    alloc_date_from = fields.Datetime.to_string(datetime.combine(fields.Date.from_string(alloc.activation_date), datetime.min.time()))
                    alloc_date_to = fields.Datetime.to_string(datetime.combine(fields.Date.from_string(alloc.expiration_date), datetime.max.time()))
                    days_to_reserve = min(days_to_reserve, alloc._get_number_of_days(
                        date_from=max(leave.date_from, alloc_date_from),
                        date_to=min(leave.date_to, alloc_date_to),
                        employee_id=leave.employee_id.id))

                self.env['hr.holidays.reservation'].sudo().create({
                    'allocation_id': alloc.id,
                    'leave_id': leave.id,
                    'days_reserved': days_to_reserve})
                days_to_take -= days_to_reserve
                if days_to_take == 0:
                    break

            if days_to_take != 0:
                raise ValidationError(_('The number of remaining leaves is not sufficient for this leave type at those dates.\n'
                                        'Please also verify the leaves waiting for validation and allocation expiration dates.'))

        return self.write({'state': 'confirm'})

    @api.multi
    def _check_security_action_approve(self):
        if not self.env.user.has_group('hr_holidays.group_hr_holidays_user'):
            raise UserError(_('Only an HR Officer or Manager can approve leave requests.'))

    @api.multi
    def action_approve(self):
        # if double_validation: this method is the first approval approval
        # if not double_validation: this method calls action_validate() below
        self._check_security_action_approve()

        current_employee = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
        if any(holiday.state != 'confirm' for holiday in self):
            raise UserError(_('Leave request must be confirmed ("To Approve") in order to approve it.'))

        self.filtered(lambda hol: hol.double_validation).write({'state': 'validate1', 'first_approver_id': current_employee.id})
        self.filtered(lambda hol: not hol.double_validation).action_validate()
        return True

    @api.multi
    def _prepare_create_by_batch(self, employee):
        self.ensure_one()
        values = {
            'name': self.name,
            'type': self.type,
            'holiday_type': 'employee',
            'holiday_status_id': self.holiday_status_id.id,
            'date_from': self.date_from,
            'date_to': self.date_to,
            'activation_date': self.activation_date,
            'expiration_date': self.expiration_date,
            'notes': self.notes,
            'number_of_days_temp': self.number_of_days_temp,
            'parent_id': self.id,
            'employee_id': employee.id
        }
        return values

    @api.multi
    def _check_security_action_validate(self):
        if not self.env.user.has_group('hr_holidays.group_hr_holidays_user'):
            raise UserError(_('Only an HR Officer or Manager can approve leave requests.'))

    @api.multi
    def action_validate(self):
        self._check_security_action_validate()

        current_employee = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
        for holiday in self:
            if holiday.state not in ['confirm', 'validate1']:
                raise UserError(_('Leave request must be confirmed in order to approve it.'))
            if holiday.state == 'validate1' and not holiday.env.user.has_group('hr_holidays.group_hr_holidays_manager'):
                raise UserError(_('Only an HR Manager can apply the second approval on leave requests.'))

            holiday.write({'state': 'validate'})
            if holiday.double_validation:
                holiday.write({'second_approver_id': current_employee.id})
            else:
                holiday.write({'first_approver_id': current_employee.id, 'second_approver_id': current_employee.id})
            if holiday.holiday_type == 'employee' and holiday.type == 'remove':
                holiday._validate_leave_request()
            elif holiday.holiday_type in ['category', 'department']:
                leaves = self.env['hr.holidays']
                employees = holiday.category_id.employee_ids if holiday.holiday_type == 'category' else holiday.department_id.member_ids
                for employee in employees:
                    values = holiday._prepare_create_by_batch(employee)
                    leaves += self.with_context(mail_notify_force_send=False).create(values)
                leaves.action_approve()
                if leaves and leaves[0].double_validation:
                    leaves.action_validate()
        return True

    def _validate_leave_request(self):
        """ Validate leave requests (holiday_type='employee' and holiday.type='remove')
        by creating a calendar event and a resource leaves. """
        for holiday in self.filtered(lambda request: request.type == 'remove' and request.holiday_type == 'employee'):
            meeting_values = holiday._prepare_holidays_meeting_values()
            meeting = self.env['calendar.event'].with_context(no_mail_to_attendees=True).create(meeting_values)
            holiday.write({'meeting_id': meeting.id})
            holiday._create_resource_leave()

    @api.multi
    def _prepare_holidays_meeting_values(self):
        self.ensure_one()
        meeting_values = {
            'name': self.display_name,
            'categ_ids': [(6, 0, [
                self.holiday_status_id.categ_id.id])] if self.holiday_status_id.categ_id else [],
            'duration': self.number_of_days_temp * HOURS_PER_DAY,
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
    def action_refuse(self):
        self._check_security_action_refuse()

        current_employee = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
        for holiday in self:
            if holiday.state not in ['confirm', 'validate', 'validate1']:
                raise UserError(_('Leave request must be confirmed or validated in order to refuse it.'))

            if holiday.state == 'validate1':
                holiday.write({'state': 'refuse', 'first_approver_id': current_employee.id})
            else:
                holiday.write({'state': 'refuse', 'second_approver_id': current_employee.id})
            # Delete the meeting
            if holiday.meeting_id:
                holiday.meeting_id.unlink()
            # Delete the reservations
            holiday.cancel_leave_reservations()
            # If a category that created several holidays, cancel all related
            holiday.linked_request_ids.action_refuse()
        self._remove_resource_leave()
        return True

    @api.multi
    def _check_security_action_refuse(self):
        if not self.env.user.has_group('hr_holidays.group_hr_holidays_user'):
            raise UserError(_('Only an HR Officer or Manager can refuse leave requests.'))

    ####################################################
    # Messaging methods
    ####################################################

    @api.multi
    def _track_subtype(self, init_values):
        if 'state' in init_values and self.state == 'validate':
            return 'hr_holidays.mt_holidays_approved'
        elif 'state' in init_values and self.state == 'validate1':
            return 'hr_holidays.mt_holidays_first_validated'
        elif 'state' in init_values and self.state == 'confirm':
            return 'hr_holidays.mt_holidays_confirmed'
        elif 'state' in init_values and self.state == 'refuse':
            return 'hr_holidays.mt_holidays_refused'
        return super(Holidays, self)._track_subtype(init_values)

    @api.multi
    def _notification_recipients(self, message, groups):
        """ Handle HR users and officers recipients that can validate or refuse leave requests
        directly from email. """
        groups = super(Holidays, self)._notification_recipients(message, groups)

        self.ensure_one()
        hr_actions = []
        if self.state == 'confirm':
            app_action = self._notification_link_helper('controller', controller='/hr_holidays/validate')
            hr_actions += [{'url': app_action, 'title': _('Approve')}]
        if self.state in ['confirm', 'validate', 'validate1']:
            ref_action = self._notification_link_helper('controller', controller='/hr_holidays/refuse')
            hr_actions += [{'url': ref_action, 'title': _('Refuse')}]

        new_group = (
            'group_hr_holidays_user', lambda partner: bool(partner.user_ids) and any(user.has_group('hr_holidays.group_hr_holidays_user') for user in partner.user_ids), {
                'actions': hr_actions,
            })

        return [new_group] + groups

    @api.multi
    def _message_notification_recipients(self, message, recipients):
        result = super(Holidays, self)._message_notification_recipients(message, recipients)
        leave_type = self.env[message.model].browse(message.res_id).type
        title = _("See Leave") if leave_type == 'remove' else _("See Allocation")
        for res in result:
            if result[res].get('button_access'):
                result[res]['button_access']['title'] = title
        return result


class HrHolidaysReservation(models.Model):
    _name = "hr.holidays.reservation"
    _description = "Leave - Allocation link"

    allocation_id = fields.Many2one('hr.holidays')
    leave_id = fields.Many2one('hr.holidays', ondelete='cascade')
    days_reserved = fields.Float('days')
