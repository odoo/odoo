# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (c) 2005-2006 Axelor SARL. (http://www.axelor.com)

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    remaining_leaves = fields.Float(compute='_compute_remaining_days', string='Remaining Legal Leaves', inverse='_inverse_remaining_days', help='Total number of legal leaves allocated to this employee, change this value to create allocation/leave request. Total based on all the leave types without overriding limit.')
    current_leave_state = fields.Selection([('draft', 'New'), ('confirm', 'Waiting Approval'),
        ('refuse', 'Refused'), ('validate1', 'Waiting Second Approval'),
        ('validate', 'Approved'), ('cancel', 'Cancelled')],
        compute='_compute_leave_status', string="Current Leave Status")
    current_leave_id = fields.Many2one('hr.holidays.status', compute='_compute_leave_status', string="Current Leave Type")
    leave_date_from = fields.Date(compute='_compute_leave_status', string='From Date')
    leave_date_to = fields.Date(compute='_compute_leave_status', string='To Date')
    leaves_count = fields.Integer(compute='_compute_leaves_count', string='Number of Leaves')
    show_leaves = fields.Boolean(compute='_compute_show_leaves', string="Able to see Remaining Leaves")
    is_absent_totay = fields.Boolean(compute='_compute_absent_employee', search='_search_absent_employee', string="Absent Today")

    def _remaining_leaves_count(self):
        leaves = self.env['hr.holidays'].read_group([('state', '=', 'validate'),
            ('holiday_status_id.limit', '=', False), ('employee_id', 'in', self.ids)],
            ['number_of_days', 'employee_id'], ['employee_id'])
        leaves = dict([(leave['employee_id'][0], leave['number_of_days']) for leave in leaves])
        return {employee.id: leaves.get(employee.id, 0) for employee in self}

    def _inverse_remaining_days(self):
        if self.remaining_leaves:
            # Find for holidays status
            status = self.env['hr.holidays.status'].search([('limit', '=', False)])
            if len(status) != 1:
                raise UserError(_("The feature behind the field 'Remaining Legal Leaves' can only be used when there is only one leave type with the option 'Allow to Override Limit' unchecked. (%s Found). Otherwise, the update is ambiguous as we cannot decide on which leave type the update has to be done. \nYou may prefer to use the classic menus 'Leave Requests' and 'Allocation Requests' located in 'Human Resources \ Leaves' to manage the leave days of the employees if the configuration does not allow to use this field.") % (len(status)))
            diff = self.remaining_leaves - self._remaining_leaves_count().get(self.id)
            if diff < 0:
                raise UserError(_('You cannot reduce validated allocation requests'))
            elif diff == 0:
                return False
            leave = self.env['hr.holidays'].create({'name': _('Allocation for %s') % self.name, 'employee_id': self.id, 'holiday_status_id': status.id, 'type': 'add', 'holiday_type': 'employee', 'number_of_days_temp': diff})
            for sig in ('confirm', 'validate', 'second_validate'):
                leave.signal_workflow(sig)
            return True
        return False

    def _compute_remaining_days(self):
        remaining_leaves = self._remaining_leaves_count()
        for employee in self:
            employee.remaining_leaves = remaining_leaves[employee.id]

    @api.depends('current_leave_id', 'leave_date_from', 'leave_date_to')
    def _compute_leave_status(self):
        holidays = self.env['hr.holidays'].search([
            ('date_from', '<=', fields.Datetime.now()),
            ('date_to', '>=', fields.Datetime.now()), ('type', '=', 'remove'),
            ('state', 'not in', ('cancel', 'refuse')),
            ('employee_id', 'in', self.ids)])
        for holiday in holidays:
            employee = holiday.employee_id
            employee.leave_date_from = holiday.date_from
            employee.leave_date_to = holiday.date_to
            employee.current_leave_state = holiday.state
            employee.current_leave_id = holiday.holiday_status_id.id

    def _compute_leaves_count(self):
        remaining_leaves = self._remaining_leaves_count()
        for employee in self.filtered(lambda e: e.id in remaining_leaves):
            employee.leaves_count = remaining_leaves[employee.id]

    def _compute_show_leaves(self):
        if self.env['res.users'].browse(self.env.uid).has_group('base.group_hr_user'):
            for employee in self:
                employee.show_leaves = True
        else:
            for employee in self.filtered(lambda e: e.user_id == self.env.user):
                employee.show_leaves = True

    def _compute_absent_employee(self):
        today_date = fields.Date.from_string(fields.Date.today())
        today_start = fields.Datetime.to_string(today_date)
        today_end = fields.Datetime.to_string(today_date + relativedelta(hours=23, minutes=59, seconds=59))
        leaves = self.env['hr.holidays'].read_group([
            ('employee_id', 'in', self.ids),
            ('state', 'not in', ['cancel', 'refuse']), ('type', '=', 'remove')],
            ('date_from', '<=', today_end), ('date_to', '>=', today_start),
            ['employee_id'], ['employee_id'])
        leaves = dict([(leave['employee_id'][0], leave['employee_id_count']) for leave in leaves])
        for employee in self:
            employee.is_absent_totay = leaves.get(employee.id)

    def _search_absent_employee(self, obj, name):
        today_date = fields.Date.from_string(fields.Date.today())
        today_start = fields.Datetime.to_string(today_date)
        today_end = fields.Datetime.to_string(today_date + relativedelta(hours=23, minutes=59, seconds=59))
        holidays = self.env['hr.holidays'].search([
            ('state', 'not in', ['cancel', 'refuse']),
            ('date_from', '<=', today_end), ('date_to', '>=', today_start),
            ('type', '=', 'remove'), ('employee_id', '!=', False)])
        return [('id', 'in', holidays.mapped('employee_id').ids)]
