# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import math
from dateutil.relativedelta import relativedelta
from datetime import datetime, date
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.addons.resource.models.resource import Intervals
from odoo.addons.resource.models.resource import HOURS_PER_DAY

class HrLeaveType(models.Model):
    _inherit = 'hr.leave.type'

    work_entry_type_id = fields.Many2one('hr.work.entry.type', string='Work Entry Type')


class HrLeave(models.Model):
    _inherit = 'hr.leave'

    @api.multi
    def _get_work_entries_values(self):
        vals_list = []
        for leave in self:
            contract = leave.employee_id._get_contracts(leave.date_from, leave.date_to, states=['open', 'pending', 'close'])
            start = max(leave.date_from, datetime.combine(contract.date_start, datetime.min.time()))
            end = min(leave.date_to, datetime.combine(contract.date_end or date.max, datetime.max.time()))
            work_entry_type = leave.holiday_status_id.work_entry_type_id
            vals_list += [{
                'name': "%s%s" % (work_entry_type.name + ": " if work_entry_type else "", leave.employee_id.name),
                'date_start': start,
                'date_stop': end,
                'work_entry_type_id': work_entry_type.id,
                'display_warning': not bool(work_entry_type),
                'employee_id': leave.employee_id.id,
                'leave_id': leave.id,
                'state': 'confirmed',
                'contract_id': contract.id,
            }]
        return vals_list

    @api.multi
    def _create_resource_leave(self):
        """
        Add a resource leave in calendars of contracts running at the same period.
        This is needed in order to compute the correct number of hours/days of the leave
        according to the contract's calender.
        """
        resource_leaves = super(HrLeave, self)._create_resource_leave()
        for resource_leave in resource_leaves:
            resource_leave.work_entry_type_id = resource_leave.holiday_id.holiday_status_id.work_entry_type_id.id

        resource_leave_values = []

        for leave in self.filtered(lambda l: l.employee_id):

            contract = leave.employee_id._get_contracts(leave.date_from, leave.date_to, states=['open', 'pending', 'close'])
            if contract and contract.resource_calendar_id != leave.employee_id.resource_calendar_id:
                resource_leave_values += [{
                    'name': leave.name,
                    'holiday_id': leave.id,
                    'resource_id': leave.employee_id.resource_id.id,
                    'work_entry_type_id': leave.holiday_status_id.work_entry_type_id.id,
                    'time_type': leave.holiday_status_id.time_type,
                    'date_from': max(leave.date_from, datetime.combine(contract.date_start, datetime.min.time())),
                    'date_to': min(leave.date_to, datetime.combine(contract.date_end or date.max, datetime.max.time())),
                    'calendar_id': contract.resource_calendar_id.id,
                }]

        return resource_leaves | self.env['resource.calendar.leaves'].create(resource_leave_values)

    @api.constrains('date_from', 'date_to')
    def _check_contracts(self):
        """
            A leave cannot be set across multiple contracts.
            Note: a leave can be across multiple contracts despite this constraint.
            It happens if a leave is correctly created (not accross multiple contracts) but
            contracts are later modifed/created in the middle of the leave.
        """
        for holiday in self:
            domain = [
                ('employee_id', '=', holiday.employee_id.id),
                ('date_start', '<=', holiday.date_to),
                ('state', 'not in', ['draft', 'cancel']),
                '|',
                    ('date_end', '>=', holiday.date_from),
                    ('date_end', '=', False),
            ]
            nbr_contracts = self.env['hr.contract'].sudo().search_count(domain)
            if nbr_contracts > 1:
                raise ValidationError(_('A leave cannot be set across multiple contracts.'))

    @api.multi
    def _cancel_work_entry_conflict(self):
        """
        Unlink any work_entry linked to a leave in self.
        Re-create new work_entries where the leaves do not cover the full range of the deleted work_entries.
        Create a leave work_entry for each leave in self.
        Return True if one or more work_entries are unlinked.
        e.g.:
            |---------------- work_entry ----------------|
                    |------ leave ------|
                            ||
                            vv
            |-benef-|---work_entry leave---|----work_entry---|
        """
        work_entries = self.env['hr.work.entry'].search([('leave_id', 'in', self.ids)])
        if work_entries:
            vals_list = self._get_work_entries_values()
            # create new work_entries where the leave does not cover the full work_entry
            work_entries_intervals = Intervals(intervals=[(b.date_start, b.date_stop, b) for b in work_entries])
            leave_intervals = Intervals(intervals=[(l.date_from, l.date_to, l) for l in self])
            remaining_work_entries = work_entries_intervals - leave_intervals

            for interval in remaining_work_entries:
                work_entry = interval[2]
                leave = work_entry.leave_id
                work_entry_type = work_entry.work_entry_type_id
                employee = work_entry.employee_id

                work_entry_start = interval[0] + relativedelta(seconds=1) if leave.date_to == interval[0] else interval[0]
                work_entry_stop = interval[1] - relativedelta(seconds=1) if leave.date_from == interval[1] else interval[1]

                vals_list += [{
                    'name': "%s: %s" % (work_entry_type.name, employee.name),
                    'date_start': work_entry_start,
                    'date_stop': work_entry_stop,
                    'work_entry_type_id': work_entry_type.id,
                    'contract_id': work_entry.contract_id.id,
                    'employee_id': employee.id,
                    'state': 'confirmed',
                }]

            date_start = min(work_entries.mapped('date_start'))
            date_stop = max(work_entries.mapped('date_stop'))
            self.env['hr.work.entry']._safe_duplicate_create(vals_list, date_start, date_stop)
            work_entries.unlink()
            return True
        return False

    @api.multi
    def action_validate(self):
        super(HrLeave, self).action_validate()
        self.sudo()._cancel_work_entry_conflict()  # delete preexisting conflicting work_entries
        return True

    @api.multi
    def action_refuse(self):
        super(HrLeave, self).action_refuse()
        work_entries = self.env['hr.work.entry'].sudo().search([('leave_id', 'in', self.ids)])
        work_entries.write({'display_warning': False, 'active': False})
        return True

    def _get_number_of_days(self, date_from, date_to, employee_id):
        """ If an employee is currently working full time but requests a leave next month
            where he has a new contract working only 3 days/week. This should be taken into
            account when computing the number of days for the leave (2 weeks leave = 6 days).
            Override this method to get number of days according to the contract's calendar
            at the time of the leave.
        """
        days = super(HrLeave, self)._get_number_of_days(date_from, date_to, employee_id)
        if employee_id:
            employee = self.env['hr.employee'].browse(employee_id)
            # Use sudo otherwise base users can't compute number of days
            contracts = employee.sudo()._get_contracts(date_from, date_to, states=['incoming', 'open', 'pending'])
            calendar = contracts[:1].resource_calendar_id if contracts else None # Note: if len(contracts)>1, the leave creation will crash because of unicity constaint
            return employee._get_work_days_data(date_from, date_to, calendar=calendar)['days']

        return days

    @api.multi
    @api.depends('number_of_days')
    def _compute_number_of_hours_display(self):
        """ Override for the same reason as _get_number_of_days()"""
        super(HrLeave, self)._compute_number_of_hours_display()
        for holiday in self:
            if holiday.date_from and holiday.date_to:
                contracts = holiday.employee_id.sudo()._get_contracts(holiday.date_from, holiday.date_to, states=['incoming', 'open', 'pending'])
                contract_calendar = contracts[:1].resource_calendar_id if contracts else None
                calendar = contract_calendar or holiday.employee_id.resource_calendar_id or self.env.user.company_id.resource_calendar_id
                holiday.number_of_hours_display = holiday.number_of_days * (calendar.hours_per_day or HOURS_PER_DAY)
