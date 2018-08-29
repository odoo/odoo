# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (c) 2005-2006 Axelor SARL. (http://www.axelor.com)

import logging

from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)


class HolidaysAllocation(models.Model):
    """ Allocation Requests Access specifications: similar to leave requests """
    _name = "hr.leave.allocation"
    _description = "Leaves Allocation"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _mail_post_access = 'read'

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
    holiday_status_id = fields.Many2one("hr.leave.type", string="Leave Type", required=True, readonly=True,
        states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]},
        domain=lambda self: self._default_domain_holiday_status_id(), default=_default_holiday_status_id)
    employee_id = fields.Many2one('hr.employee', string='Employee', index=True, readonly=True,
        states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]}, default=_default_employee, track_visibility='onchange')
    notes = fields.Text('Reasons', readonly=True, states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    number_of_days_temp = fields.Float(
        'Allocation', copy=False, readonly=True,
        states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]},
        help='Number of days of the leave request according to your working schedule.')
    number_of_days = fields.Float('Number of Days', compute='_compute_number_of_days', store=True, track_visibility='onchange')
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

    _sql_constraints = [
        ('type_value', "CHECK( (holiday_type='employee' AND employee_id IS NOT NULL) or (holiday_type='category' AND category_id IS NOT NULL) or (holiday_type='department' AND department_id IS NOT NULL) )",
         "The employee, department or employee category of this request is missing. Please make sure that your user login is linked to an employee."),
        ('date_check', "CHECK ( number_of_days_temp >= 0 )", "The number of days must be greater than 0."),
    ]

    @api.multi
    @api.depends('number_of_days_temp')
    def _compute_number_of_days(self):
        for holiday in self:
            holiday.number_of_days = holiday.number_of_days_temp

    @api.multi
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
                if allocation.state == 'confirm' and allocation.holiday_status_id.validation_type == 'both':
                    allocation._check_approval_update('validate1')
                else:
                    allocation._check_approval_update('validate')
            except (AccessError, UserError):
                allocation.can_approve = False
            else:
                allocation.can_approve = True

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

    ####################################################
    # ORM Overrides methods
    ####################################################

    @api.multi
    def name_get(self):
        res = []
        for leave in self:
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
                vstart = fields.Datetime.from_string(allocation.holiday_status_id.validity_start)
                vstop = fields.Datetime.from_string(allocation.holiday_status_id.validity_stop)
                today = fields.Datetime.from_string(fields.Datetime.now())

                if vstart > today or vstop < today:
                    raise UserError(_('You can allocate %s only between %s and %s') % (allocation.holiday_status_id.display_name,
                                                                                  allocation.holiday_status_id.validity_start, allocation.holiday_status_id.validity_stop))

    @api.model
    def create(self, values):
        """ Override to avoid automatic logging of creation """
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
        if values.get('state'):
            self._check_approval_update(values['state'])
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
        if any(holiday.state != 'confirm' for holiday in self):
            raise UserError(_('Leave request must be confirmed ("To Approve") in order to approve it.'))

        current_employee = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)

        self.filtered(lambda hol: hol.validation_type == 'both').write({'state': 'validate1', 'first_approver_id': current_employee.id})
        self.filtered(lambda hol: not hol.validation_type == 'both').action_validate()
        self.activity_update()
        return True

    @api.multi
    def action_validate(self):
        current_employee = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
        for holiday in self:
            if holiday.state not in ['confirm', 'validate1']:
                raise UserError(_('Leave request must be confirmed in order to approve it.'))

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
                    'hr_holidays.mail_act_leave_allocation_approval', fields.Date.today(),
                    user_id=allocation.sudo()._get_responsible_for_approval().id)
            elif allocation.state == 'validate1':
                allocation.activity_feedback(['hr_holidays.mail_act_leave_allocation_approval'])
                allocation.activity_schedule(
                    'hr_holidays.mail_act_leave_allocation_second_approval', fields.Date.today(),
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

        new_group = (
            'group_hr_holidays_user', lambda partner: bool(partner.user_ids) and any(user.has_group('hr_holidays.group_hr_holidays_user') for user in partner.user_ids), {
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
