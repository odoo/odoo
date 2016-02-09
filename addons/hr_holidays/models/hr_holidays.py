# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (c) 2005-2006 Axelor SARL. (http://www.axelor.com)

import math
from datetime import timedelta
from werkzeug import url_encode

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError, ValidationError


class HrHolidays(models.Model):
    _name = "hr.holidays"
    _description = "Leave"
    _order = "type desc, date_from desc"
    _inherit = ['mail.thread', 'ir.needaction_mixin']

    def _default_employee_id(self):
        if self.env.context.get('default_employee_id'):
            return self.env.context['default_employee_id']
        return self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1).id

    name = fields.Char(string='Description')
    state = fields.Selection([
        ('draft', 'To Submit'),
        ('cancel', 'Cancelled'),
        ('confirm', 'To Approve'),
        ('refuse', 'Refused'),
        ('validate1', 'Second Approval'),
        ('validate', 'Approved')
    ], string='Status', readonly=True, track_visibility='onchange', copy=False,
        help="The status is set to 'To Submit', when a holiday request is created.\
              \nThe status is 'To Approve', when holiday request is confirmed by user.\
              \nThe status is 'Refused', when holiday request is refused by manager.\
              \nThe status is 'Approved', when holiday request is approved by manager.",
        default='confirm')
    payslip_status = fields.Boolean(string='Reported in last payslips',
        help='Green this button when the leave has been taken into account in the payslip.')
    report_note = fields.Text(string='HR Comments')
    user_id = fields.Many2one('res.users', string='User',
        store=True, default=lambda self: self.env.uid,
        related='employee_id.user_id', readonly=True)
    date_from = fields.Datetime(string='Start Date', readonly=True,
        states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]},
        index=True, copy=False)
    date_to = fields.Datetime(string='End Date', readonly=True, copy=False,
        states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    holiday_status_id = fields.Many2one("hr.holidays.status",
        string="Leave Type", required=True, readonly=True,
        states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    employee_id = fields.Many2one('hr.employee',
        string="Employee", index=True, readonly=True,
        states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]},
        default=_default_employee_id)
    manager_id = fields.Many2one('hr.employee',
        string='First Approval', readonly=True, copy=False,
        help='This area is automatically filled by the user who validate the leave')
    notes = fields.Text(string='Reasons', readonly=True,
        states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    number_of_days_temp = fields.Float(string='Allocation', readonly=True,
        states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]},
        copy=False)
    number_of_days = fields.Float(compute='_compute_number_of_days',
        string='Number of Days', store=True)
    meeting_id = fields.Many2one('calendar.event', string='Meeting')
    type = fields.Selection([
        ('remove', 'Leave Request'),
        ('add', 'Allocation Request')
    ], string='Request Type', required=True, readonly=True, index=True,
        states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]},
        help="Choose 'Leave Request' if someone wants to take an off-day."
             "\nChoose 'Allocation Request' if you want to  increase the number of leaves available for someone",
        default='remove')
    parent_id = fields.Many2one('hr.holidays', string='Parent')
    linked_request_ids = fields.One2many('hr.holidays', 'parent_id', string='Linked Requests')
    department_id = fields.Many2one('hr.department',
        related='employee_id.department_id', string='Department', readonly=True, store=True)
    category_id = fields.Many2one('hr.employee.category',
        string="Employee Tag", help='Category of Employee', readonly=True,
        states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    holiday_type = fields.Selection([
        ('employee', 'By Employee'),
        ('category', 'By Employee Tag')
    ], string='Allocation Mode', readonly=True, required=True,
        states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]},
        help='By Employee: Allocation/Request for individual Employee, By Employee Tag: Allocation/Request for group of employees in category',
        default='employee')
    manager_id2 = fields.Many2one('hr.employee',
        string='Second Approval', readonly=True, copy=False,
        help='This area is automaticly filled by the user who validate the leave with second level (If Leave type need second validation)')
    double_validation = fields.Boolean(comodel_name='hr.holidays.status',
        related='holiday_status_id.double_validation', string='Apply Double Validation')
    can_reset = fields.Boolean(compute='_compute_can_reset', string="Can reset")

    _sql_constraints = [
        ('type_value', "CHECK( \
            (holiday_type='employee' AND employee_id IS NOT NULL) or \
            (holiday_type='category' AND category_id IS NOT NULL) \
        )", _("The employee or employee category of this request is missing."
              " Please make sure that your user login is linked to an employee.")),
        ('date_check2', "CHECK ( \
            (type='add') OR (date_from <= date_to) \
            )", _("The start date must be anterior to the end date.")),
        ('date_check', "CHECK ( number_of_days_temp >= 0 )",
            _("The number of days must be greater than 0.")),
    ]

    @api.depends('number_of_days_temp')
    def _compute_number_of_days(self):
        for holiday in self:
            if holiday.type == 'remove':
                holiday.number_of_days = -holiday.number_of_days_temp
            else:
                holiday.number_of_days = holiday.number_of_days_temp

    def _compute_can_reset(self):
        """User can reset a leave request if it is its own leave request or if
        he is an Hr Manager. """
        if self.env['res.users'].browse(self.env.uid).has_group('base.group_hr_manager'):
            for holiday in self:
                holiday.can_reset = True
        else:
            for holiday in self.filtered(lambda h: h.employee_id and h.employee_id.user_id == self.env.user):
                holiday.can_reset = True

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
            leaves_taken = self.search_count(domain)
            if leaves_taken:
                raise ValidationError(_('You can not have 2 leaves that overlaps on same day!'))

    @api.constrains('state', 'number_of_days_temp')
    def _check_holiday(self):
        for holiday in self.filtered(lambda h: h.holiday_type == 'employee' and h.type == 'remove' and h.employee_id and not h.holiday_status_id.limit):
            leave_days = holiday.holiday_status_id.get_days(holiday.employee_id.id)[holiday.holiday_status_id.id]
            if leave_days['remaining_leaves'] < 0 or leave_days['virtual_remaining_leaves'] < 0:
                raise ValidationError(_('The number of remaining leaves is not sufficient for this leave type.\n Please verify also the leaves waiting for validation.'))

    @api.multi
    def name_get(self):
        return [(leave.id, leave.name or _("%s on %s") % (leave.employee_id.name, leave.holiday_status_id.name)) for leave in self]

    @api.onchange('holiday_type')
    def _onchange_holiday_type(self):
        if self.holiday_type == 'employee' and not self.employee_id:
            self.employee_id = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1).id
        elif self.holiday_type != 'employee':
            self.employee_id = False

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        self.department_id = self.employee_id.department_id

    # TODO: can be improved using resource calendar method
    def _get_number_of_days(self, date_from, date_to):
        """Returns a float equals to the timedelta between two dates given as string."""
        from_dt = fields.Datetime.from_string(date_from)
        to_dt = fields.Datetime.from_string(date_to)
        diff = to_dt - from_dt
        diff_day = diff.days + float(diff.seconds) / 86400
        return diff_day

    @api.onchange('date_from')
    def _onchange_date_from(self):
        """
        If there are no date set for date_to, automatically set one 8 hours later than
        the date_from.
        Also update the number_of_days.
        """
        # date_to has to be greater than date_from
        if (self.date_from and self.date_to) and (self.date_from > self.date_to):
            raise UserError(_('The start date must be anterior to the end date.'))

        # No date_to set so far: automatically compute one 8 hours later
        if self.date_from and not self.date_to:
            date_from = fields.Datetime.from_string(self.date_from)
            date_to_with_delta = date_from + timedelta(hours=8)
            self.date_to = fields.Datetime.to_string(date_to_with_delta)

        # Compute and update the number of days
        if (self.date_to and self.date_from) and (self.date_from <= self.date_to):
            diff_day = self._get_number_of_days(self.date_from, self.date_to)
            self.number_of_days_temp = round(math.floor(diff_day)) + 1
        else:
            self.number_of_days_temp = 0

    @api.onchange('date_to')
    def _onchange_date_to(self):
        """
        Update the number_of_days.
        """
        # date_to has to be greater than date_from
        if (self.date_from and self.date_to) and (self.date_from > self.date_to):
            raise UserError(_('The start date must be anterior to the end date.'))

        # Compute and update the number of days
        if (self.date_to and self.date_from) and (self.date_from <= self.date_to):
            diff_day = self._get_number_of_days(self.date_from, self.date_to)
            self.number_of_days_temp = round(math.floor(diff_day)) + 1
        else:
            self.number_of_days_temp = 0

    def _check_state_access_right(self, vals):
        if vals.get('state') and vals['state'] not in ['draft', 'confirm', 'cancel'] and not self.env.user.has_group('base.group_hr_user'):
            return False
        return True

    def add_follower(self, employee_id):
        employee = self.env['hr.employee'].browse(employee_id)
        if employee.user_id:
            self.message_subscribe_users(user_ids=[employee.user_id.id])

    @api.model
    def create(self, values):
        """ Override to avoid automatic logging of creation """
        employee_id = values.get('employee_id')
        context = dict(self.env.context, mail_create_nolog=True, mail_create_nosubscribe=True)
        if not self._check_state_access_right(values):
            raise AccessError(_('You cannot set a leave request as \'%s\'. Contact a human resource manager.') % values.get('state'))
        if not values.get('name'):
            employee_name = self.env['hr.employee'].browse(employee_id).name
            holiday_type = self.env['hr.holidays.status'].browse(values.get('holiday_status_id')).name
            values['name'] = _("%s on %s") % (employee_name, holiday_type)
        hr_holiday = super(HrHolidays, self.with_context(context)).create(values)
        hr_holiday.with_context(context).add_follower(employee_id)
        return hr_holiday

    @api.multi
    def write(self, vals):
        employee_id = vals.get('employee_id')
        if not self._check_state_access_right(vals):
            raise AccessError(_('You cannot set a leave request as \'%s\'. Contact a human resource manager.') % vals.get('state'))
        hr_holidays = super(HrHolidays, self).write(vals)
        self.add_follower(employee_id)
        return hr_holidays

    @api.multi
    def unlink(self):
        for holiday in self:
            if holiday.state not in ['draft', 'cancel', 'confirm']:
                raise UserError(_('You cannot delete a leave which is in %s state.') % (holiday.state,))
        return super(HrHolidays, self).unlink()

    def _create_resource_leave(self):
        '''This method will create entry in resource calendar leave object at the time of holidays validated '''
        ResourceCalendarLeaves = self.env['resource.calendar.leaves']
        for leave in self:
            vals = {
                'name': leave.name,
                'date_from': leave.date_from,
                'holiday_id': leave.id,
                'date_to': leave.date_to,
                'resource_id': leave.employee_id.resource_id.id,
                'calendar_id': leave.employee_id.resource_id.calendar_id.id
            }
            ResourceCalendarLeaves.create(vals)
        return True

    def _remove_resource_leave(self):
        '''This method will create entry in resource calendar leave object at the time of holidays cancel/removed'''
        return self.env['resource.calendar.leaves'].search([('holiday_id', 'in', self.ids)]).unlink()

    @api.multi
    def holidays_reset(self):
        self.write({
            'state': 'draft',
            'manager_id': False,
            'manager_id2': False,
        })
        linked_requests = self.mapped('linked_request_ids')
        if linked_requests:
            linked_requests.holidays_reset()
            linked_requests.unlink()
        return True

    @api.multi
    def holidays_first_validate(self):
        manager = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
        return self.write({'state': 'validate1', 'manager_id': manager.id})

    @api.multi
    def holidays_validate(self):
        CalendarEvent = self.env['calendar.event']
        manager = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
        for holiday in self:
            holiday.state = 'validate'
            if holiday.double_validation:
                holiday.manager_id2 = manager.id
            else:
                holiday.manager_id = manager.id

            if holiday.holiday_type == 'employee' and holiday.type == 'remove':
                meeting_vals = {
                    'name': holiday.display_name,
                    'categ_ids': holiday.holiday_status_id.categ_id and [(6, 0, [holiday.holiday_status_id.categ_id.id])] or [],
                    'duration': holiday.number_of_days_temp * 8,
                    'description': holiday.notes,
                    'user_id': holiday.user_id.id,
                    'start': holiday.date_from,
                    'stop': holiday.date_to,
                    'allday': False,
                    'state': 'open',            # to block that meeting date in the calendar
                    'class': 'confidential'
                }
                #Add the partner_id (if exist) as an attendee
                if holiday.user_id.partner_id:
                    meeting_vals['partner_ids'] = [(4, holiday.user_id.partner_id.id)]

                meeting = CalendarEvent.with_context(no_email=True).create(meeting_vals)
                holiday._create_resource_leave()
                self.write({'meeting_id': meeting.id})
            elif holiday.holiday_type == 'category':
                leaves = []
                for emp in holiday.category_id.employee_ids:
                    vals = {
                        'name': holiday.name,
                        'type': holiday.type,
                        'holiday_type': 'employee',
                        'holiday_status_id': holiday.holiday_status_id.id,
                        'date_from': holiday.date_from,
                        'date_to': holiday.date_to,
                        'notes': holiday.notes,
                        'number_of_days_temp': holiday.number_of_days_temp,
                        'parent_id': holiday.id,
                        'employee_id': emp.id
                    }
                    leaves.append(self.with_context(mail_notify_force_send=False).create(vals))
                for leave in leaves:
                    # TODO is it necessary to interleave the calls?
                    for sig in ('confirm', 'validate', 'second_validate'):
                        leave.signal_workflow(sig)
        return True

    @api.multi
    def holidays_confirm(self):
        return self.write({'state': 'confirm'})

    @api.multi
    def holidays_refuse(self):
        manager = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
        for holiday in self:
            if holiday.state == 'validate1':
                holiday.write({'state': 'refuse', 'manager_id': manager.id})
            else:
                holiday.write({'state': 'refuse', 'manager_id2': manager.id})
        self.holidays_cancel()
        return True

    @api.multi
    def holidays_cancel(self):
        for holiday in self:
            # Delete the meeting
            holiday.meeting_id.unlink()

            # If a category that created several holidays, cancel all related
            holiday.linked_request_ids.signal_workflow('refuse')

        self._remove_resource_leave()
        return True

    @api.multi
    def toggle_payslip_status(self):
        for holiday in self:
            holiday.payslip_status = not holiday.payslip_status
        return True

    @api.multi
    def _track_subtype(self, init_values):
        self.ensure_one()
        if 'state' in init_values:
            states = {
                'validate': 'hr_holidays.mt_holidays_approved',
                'validate1': 'hr_holidays.mt_holidays_first_validated',
                'confirm': 'hr_holidays.mt_holidays_confirmed',
                'refuse': 'hr_holidays.mt_holidays_refused'
            }
            return states.get(self.state)
        return super(HrHolidays, self)._track_subtype(init_values)

    @api.multi
    def _notification_group_recipients(self, message, recipients, done_ids, group_data):
        """ Override the mail.thread method to handle HR users and officers
        recipients. Indeed those will have specific action in their notification
        emails. """
        recipients_to_add = recipients.filtered(lambda r: r.id not in done_ids and r.user_ids and r.user_ids[0].has_group('base.group_hr_user'))
        group_data['group_hr_user'] |= recipients_to_add
        done_ids.update(recipients_to_add.ids)
        return super(HrHolidays, self)._notification_group_recipients(message, recipients, done_ids, group_data)

    @api.multi
    def _notification_get_recipient_groups(self, message, recipients):
        self.ensure_one()
        res = super(HrHolidays, self)._notification_get_recipient_groups(message, recipients)
        app_action = '/mail/workflow?%s' % url_encode({'model': self._name, 'res_id': self.id, 'signal': 'validate'})
        ref_action = '/mail/workflow?%s' % url_encode({'model': self._name, 'res_id': self.id, 'signal': 'refuse'})

        actions = []
        if self.state == 'confirm':
            actions.append({'url': app_action, 'title': 'Approve'})
        if self.state in ['confirm', 'validate', 'validate1']:
            actions.append({'url': ref_action, 'title': 'Refuse'})

        res['group_hr_user'] = {
            'actions': actions
        }
        return res
