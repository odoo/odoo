# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (c) 2005-2006 Axelor SARL. (http://www.axelor.com)

import logging
import math
from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError, AccessError, ValidationError
from odoo.tools import float_compare
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)


HOURS_PER_DAY = 8

class HolidaysRequest(models.Model):
    _name = "hr.leave"
    _description = "Leave"
    _order = "date_from desc"
    _inherit = ['mail.thread']

    def _default_employee(self):
        return self.env.context.get('default_employee_id') or self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)

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
    payslip_status = fields.Boolean('Reported in last payslips',
        help='Green this button when the leave has been taken into account in the payslip.')
    report_note = fields.Text('HR Comments')
    user_id = fields.Many2one('res.users', string='User', related='employee_id.user_id', related_sudo=True, store=True, default=lambda self: self.env.uid, readonly=True)
    date_from = fields.Datetime('Start Date', readonly=True, index=True, copy=False, required=True,
        states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]}, track_visibility='onchange')
    date_to = fields.Datetime('End Date', readonly=True, copy=False, required=True,
        states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]}, track_visibility='onchange')
    holiday_status_id = fields.Many2one("hr.leave.type", string="Leave Type", required=True, readonly=True,
        states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    employee_id = fields.Many2one('hr.employee', string='Employee', index=True, readonly=True,
        states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]}, default=_default_employee, track_visibility='onchange')
    manager_id = fields.Many2one('hr.employee', related='employee_id.parent_id', string='Manager', readonly=True, store=True)
    notes = fields.Text('Reasons', readonly=True, states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    number_of_days_temp = fields.Float(
        'Allocation', copy=False, readonly=True,
        states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]},
        help='Number of days of the leave request according to your working schedule.')
    number_of_days = fields.Float('Number of Days', compute='_compute_number_of_days', store=True, track_visibility='onchange')
    meeting_id = fields.Many2one('calendar.event', string='Meeting')

    parent_id = fields.Many2one('hr.leave', string='Parent')
    linked_request_ids = fields.One2many('hr.leave', 'parent_id', string='Linked Requests')
    department_id = fields.Many2one('hr.department', string='Department', readonly=True, states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    category_id = fields.Many2one('hr.employee.category', string='Employee Tag', readonly=True,
        states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]}, help='Category of Employee')
    holiday_type = fields.Selection([
        ('employee', 'By Employee'),
        ('department', 'By Department'),
        ('category', 'By Employee Tag')
    ], string='Allocation Mode', readonly=True, required=True, default='employee',
        states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]},
        help='By Employee: Allocation/Request for individual Employee, By Employee Tag: Allocation/Request for group of employees in category')
    first_approver_id = fields.Many2one('hr.employee', string='First Approval', readonly=True, copy=False,
        help='This area is automatically filled by the user who validate the leave', oldname='manager_id')
    second_approver_id = fields.Many2one('hr.employee', string='Second Approval', readonly=True, copy=False, oldname='manager_id2',
        help='This area is automaticly filled by the user who validate the leave with second level (If Leave type need second validation)')
    double_validation = fields.Boolean('Apply Double Validation', related='holiday_status_id.double_validation')
    can_reset = fields.Boolean('Can reset', compute='_compute_can_reset')

    _sql_constraints = [
        ('type_value', "CHECK( (holiday_type='employee' AND employee_id IS NOT NULL) or (holiday_type='category' AND category_id IS NOT NULL) or (holiday_type='department' AND department_id IS NOT NULL) )",
         "The employee, department or employee category of this request is missing. Please make sure that your user login is linked to an employee."),
        ('date_check2', "CHECK ((date_from <= date_to))", "The start date must be anterior to the end date."),
        ('date_check', "CHECK ( number_of_days_temp >= 0 )", "The number of days must be greater than 0."),
    ]

    @api.multi
    @api.depends('number_of_days_temp')
    def _compute_number_of_days(self):
        for holiday in self:
            holiday.number_of_days = -holiday.number_of_days_temp

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

    @api.onchange('date_from')
    def _onchange_date_from(self):
        """ If there are no date set for date_to, automatically set one 8 hours later than
            the date_from. Also update the number_of_days.
        """
        date_from = self.date_from
        date_to = self.date_to

        # No date_to set so far: automatically compute one 8 hours later
        if date_from and not date_to:
            date_to_with_delta = fields.Datetime.from_string(date_from) + timedelta(hours=HOURS_PER_DAY)
            self.date_to = str(date_to_with_delta)

        # Compute and update the number of days
        if (date_to and date_from) and (date_from <= date_to):
            self.number_of_days_temp = self._get_number_of_days(date_from, date_to, self.employee_id.id)
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

    @api.constrains('date_from', 'date_to')
    def _check_date(self):
        for holiday in self:
            domain = [
                ('date_from', '<=', holiday.date_to),
                ('date_to', '>=', holiday.date_from),
                ('employee_id', '=', holiday.employee_id.id),
                ('id', '!=', holiday.id),
                ('state', 'not in', ['cancel', 'refuse']),
            ]
            nholidays = self.search_count(domain)
            if nholidays:
                raise ValidationError(_('You can not have 2 leaves that overlaps on same day!'))

    @api.constrains('state', 'number_of_days_temp')
    def _check_holidays(self):
        for holiday in self:
            if holiday.holiday_type != 'employee' or not holiday.employee_id or holiday.holiday_status_id.limit:
                continue
            leave_days = holiday.holiday_status_id.get_days(holiday.employee_id.id)[holiday.holiday_status_id.id]
            if float_compare(leave_days['remaining_leaves'], 0, precision_digits=2) == -1 or \
              float_compare(leave_days['virtual_remaining_leaves'], 0, precision_digits=2) == -1:
                raise ValidationError(_('The number of remaining leaves is not sufficient for this leave type.\n'
                                        'Please verify also the leaves waiting for validation.'))

    def _get_number_of_days(self, date_from, date_to, employee_id):
        """ Returns a float equals to the timedelta between two dates given as string."""
        from_dt = fields.Datetime.from_string(date_from)
        to_dt = fields.Datetime.from_string(date_to)

        if employee_id:
            employee = self.env['hr.employee'].browse(employee_id)
            return employee.get_work_days_count(from_dt, to_dt)

        time_delta = to_dt - from_dt
        return math.ceil(time_delta.days + float(time_delta.seconds) / 86400)

    ####################################################
    # ORM Overrides methods
    ####################################################

    @api.multi
    def name_get(self):
        res = []
        for leave in self:
            if self.env.context.get('short_name'):
                res.append((leave.id, _("%s : %.2f day(s)") % (leave.name or leave.holiday_status_id.name, leave.number_of_days_temp)))
            else:
                res.append((leave.id, _("%s on %s : %.2f day(s)") % (leave.employee_id.name or leave.category_id.name, leave.holiday_status_id.name, leave.number_of_days_temp)))
        return res

    @api.multi
    def add_follower(self, employee_id):
        employee = self.env['hr.employee'].browse(employee_id)
        if employee.user_id:
            self.message_subscribe_users(user_ids=employee.user_id.ids)

    @api.model
    def create(self, values):
        """ Override to avoid automatic logging of creation """
        employee_id = values.get('employee_id', False)
        if not values.get('department_id'):
            values.update({'department_id': self.env['hr.employee'].browse(employee_id).department_id.id})
        holiday = super(HolidaysRequest, self.with_context(mail_create_nolog=True, mail_create_nosubscribe=True)).create(values)
        holiday.add_follower(employee_id)
        return holiday

    @api.multi
    def write(self, values):
        employee_id = values.get('employee_id', False)
        result = super(HolidaysRequest, self).write(values)
        self.add_follower(employee_id)
        return result

    @api.multi
    def unlink(self):
        for holiday in self.filtered(lambda holiday: holiday.state not in ['draft', 'cancel', 'confirm']):
            raise UserError(_('You cannot delete a leave which is in %s state.') % (holiday.state,))
        return super(HolidaysRequest, self).unlink()

    @api.multi
    def copy_data(self, default=None):
        raise UserError(_('A leave cannot be duplicated.'))

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

    def _validate_leave_request(self):
        """ Validate leave requests (holiday_type='employee')
        by creating a calendar event and a resource leaves. """
        for holiday in self.filtered(lambda request: request.holiday_type == 'employee'):
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
    def _prepare_holiday_values(self, employee):
        self.ensure_one()
        values = {
            'name': self.name,
            'holiday_type': 'employee',
            'holiday_status_id': self.holiday_status_id.id,
            'date_from': self.date_from,
            'date_to': self.date_to,
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
        return True

    @api.multi
    def action_confirm(self):
        if self.filtered(lambda holiday: holiday.state != 'draft'):
            raise UserError(_('Leave request must be in Draft state ("To Submit") in order to confirm it.'))
        return self.write({'state': 'confirm'})

    @api.multi
    def action_approve(self):
        # if double_validation: this method is the first approval approval
        # if not double_validation: this method calls action_validate() below
        if not self.env.user.has_group('hr_holidays.group_hr_holidays_user'):
            raise UserError(_('Only an HR Officer or Manager can approve leave requests.'))

        current_employee = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
        if any(holiday.state != 'confirm' for holiday in self):
            raise UserError(_('Leave request must be confirmed ("To Approve") in order to approve it.'))

        self.filtered(lambda hol: hol.double_validation).write({'state': 'validate1', 'first_approver_id': current_employee.id})
        self.filtered(lambda hol: not hol.double_validation).action_validate()
        return True

    @api.multi
    def action_validate(self):
        if not self.env.user.has_group('hr_holidays.group_hr_holidays_user'):
            raise UserError(_('Only an HR Officer or Manager can approve leave requests.'))

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
                holiday.write({'first_approver_id': current_employee.id})
            if holiday.holiday_type == 'employee':
                holiday._validate_leave_request()
            elif holiday.holiday_type in ['category', 'department']:
                leaves = self.env['hr.leave']
                employees = holiday.category_id.employee_ids if holiday.holiday_type == 'category' else holiday.department_id.member_ids
                for employee in employees:
                    values = holiday._prepare_holiday_values(employee)
                    leaves += self.with_context(mail_notify_force_send=False).create(values)
                # TODO is it necessary to interleave the calls?
                leaves.action_approve()
                if leaves and leaves[0].double_validation:
                    leaves.action_validate()
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
            # Delete the meeting
            if holiday.meeting_id:
                holiday.meeting_id.unlink()
            # If a category that created several holidays, cancel all related
            holiday.linked_request_ids.action_refuse()
        self._remove_resource_leave()
        return True

    ####################################################
    # Messaging methods
    ####################################################

    @api.multi
    def _track_subtype(self, init_values):
        if 'state' in init_values and self.state == 'validate':
            return 'hr_holidays.mt_leave_approved'
        elif 'state' in init_values and self.state == 'validate1':
            return 'hr_holidays.mt_leave_first_validated'
        elif 'state' in init_values and self.state == 'confirm':
            return 'hr_holidays.mt_leave_confirmed'
        elif 'state' in init_values and self.state == 'refuse':
            return 'hr_holidays.mt_leave_refused'
        return super(HolidaysRequest, self)._track_subtype(init_values)

    @api.multi
    def _notification_recipients(self, message, groups):
        """ Handle HR users and officers recipients that can validate or refuse holidays
        directly from email. """
        groups = super(HolidaysRequest, self)._notification_recipients(message, groups)

        self.ensure_one()
        hr_actions = []
        if self.state == 'confirm':
            app_action = self._notification_link_helper('controller', controller='/leave/validate')
            hr_actions += [{'url': app_action, 'title': _('Approve')}]
        if self.state in ['confirm', 'validate', 'validate1']:
            ref_action = self._notification_link_helper('controller', controller='/leave/refuse')
            hr_actions += [{'url': ref_action, 'title': _('Refuse')}]

        new_group = (
            'group_hr_holidays_user', lambda partner: bool(partner.user_ids) and any(user.has_group('hr_holidays.group_hr_holidays_user') for user in partner.user_ids), {
                'actions': hr_actions,
            })

        return [new_group] + groups

    @api.multi
    def _message_notification_recipients(self, message, recipients):
        result = super(HolidaysRequest, self)._message_notification_recipients(message, recipients)
        title = _("See Leave")
        for res in result:
            if result[res].get('button_access'):
                result[res]['button_access']['title'] = title
        return result
