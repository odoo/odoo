# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from datetime import datetime, date

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.osv.expression import AND
from odoo.tools import format_date


class HrLeaveType(models.Model):
    _inherit = 'hr.leave.type'

    work_entry_type_id = fields.Many2one('hr.work.entry.type', string='Work Entry Type')


class HrLeave(models.Model):
    _inherit = 'hr.leave'

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
            contracts = leave.employee_id.sudo()._get_contracts(leave.date_from, leave.date_to, states=['open'])
            for contract in contracts:
                if contract and contract.resource_calendar_id != leave.employee_id.resource_calendar_id:
                    resource_leave_values += [{
                        'name': _("%s: Time Off", leave.employee_id.name),
                        'holiday_id': leave.id,
                        'resource_id': leave.employee_id.resource_id.id,
                        'work_entry_type_id': leave.holiday_status_id.work_entry_type_id.id,
                        'time_type': leave.holiday_status_id.time_type,
                        'date_from': max(leave.date_from, datetime.combine(contract.date_start, datetime.min.time())),
                        'date_to': min(leave.date_to, datetime.combine(contract.date_end or date.max, datetime.max.time())),
                        'calendar_id': contract.resource_calendar_id.id,
                    }]

        return resource_leaves | self.env['resource.calendar.leaves'].create(resource_leave_values)

    def _get_overlapping_contracts(self, contract_states=None):
        self.ensure_one()
        if contract_states is None:
            contract_states = [
                '|',
                ('state', 'not in', ['draft', 'cancel']),
                '&',
                ('state', '=', 'draft'),
                ('kanban_state', '=', 'done')
            ]
        domain = AND([contract_states, [
            ('employee_id', '=', self.employee_id.id),
            ('date_start', '<=', self.date_to),
            '|',
                ('date_end', '>=', self.date_from),
                '&',
                    ('date_end', '=', False),
                    ('state', '!=', 'close')
        ]])
        return self.env['hr.contract'].sudo().search(domain)

    @api.constrains('date_from', 'date_to')
    def _check_contracts(self):
        """
            A leave cannot be set across multiple contracts.
            Note: a leave can be across multiple contracts despite this constraint.
            It happens if a leave is correctly created (not across multiple contracts) but
            contracts are later modifed/created in the middle of the leave.
        """
        for holiday in self.filtered('employee_id'):
            contracts = holiday._get_overlapping_contracts()
            if len(contracts.resource_calendar_id) > 1:
                state_labels = {e[0]: e[1] for e in contracts._fields['state']._description_selection(self.env)}
                raise ValidationError(
                    _("""A leave cannot be set across multiple contracts with different working schedules.

Please create one time off for each contract.

Time off:
%s

Contracts:
%s""",
                      holiday.display_name,
                      '\n'.join(_(
                          "Contract %s from %s to %s, status: %s",
                          contract.name,
                          format_date(self.env, contract.date_start),
                          format_date(self.env, contract.date_start) if contract.date_end else _("undefined"),
                          state_labels[contract.state]
                      ) for contract in contracts)))

    def _cancel_work_entry_conflict(self):
        """
        Creates a leave work entry for each hr.leave in self.
        Check overlapping work entries with self.
        Work entries completely included in a leave are archived.
        e.g.:
            |----- work entry ----|---- work entry ----|
                |------------------- hr.leave ---------------|
                                    ||
                                    vv
            |----* work entry ****|
                |************ work entry leave --------------|
        """
        if not self:
            return

        # 1. Create a work entry for each leave
        work_entries_vals_list = []
        for leave in self:
            contracts = leave.employee_id.sudo()._get_contracts(leave.date_from, leave.date_to, states=['open', 'close'])
            for contract in contracts:
                # Generate only if it has aleady been generated
                if leave.date_to >= contract.date_generated_from and leave.date_from <= contract.date_generated_to:
                    work_entries_vals_list += contracts._get_work_entries_values(leave.date_from, leave.date_to)

        new_leave_work_entries = self.env['hr.work.entry'].create(work_entries_vals_list)

        if new_leave_work_entries:
            # 2. Fetch overlapping work entries, grouped by employees
            start = min(self.mapped('date_from'), default=False)
            stop = max(self.mapped('date_to'), default=False)
            work_entry_groups = self.env['hr.work.entry']._read_group([
                ('date_start', '<', stop),
                ('date_stop', '>', start),
                ('employee_id', 'in', self.employee_id.ids),
            ], ['work_entry_ids:array_agg(id)', 'employee_id'], ['employee_id', 'date_start', 'date_stop'], lazy=False)
            work_entries_by_employee = defaultdict(lambda: self.env['hr.work.entry'])
            for group in work_entry_groups:
                employee_id = group.get('employee_id')[0]
                work_entries_by_employee[employee_id] |= self.env['hr.work.entry'].browse(group.get('work_entry_ids'))

            # 3. Archive work entries included in leaves
            included = self.env['hr.work.entry']
            overlappping = self.env['hr.work.entry']
            for work_entries in work_entries_by_employee.values():
                # Work entries for this employee
                new_employee_work_entries = work_entries & new_leave_work_entries
                previous_employee_work_entries = work_entries - new_leave_work_entries

                # Build intervals from work entries
                leave_intervals = new_employee_work_entries._to_intervals()
                conflicts_intervals = previous_employee_work_entries._to_intervals()

                # Compute intervals completely outside any leave
                # Intervals are outside, but associated records are overlapping.
                outside_intervals = conflicts_intervals - leave_intervals

                overlappping |= self.env['hr.work.entry']._from_intervals(outside_intervals)
                included |= previous_employee_work_entries - overlappping
            overlappping.write({'leave_id': False})
            included.write({'active': False})

    def write(self, vals):
        if not self:
            return True
        skip_check = not bool({'employee_id', 'state', 'date_from', 'date_to'} & vals.keys())

        start = min(self.mapped('date_from') + [fields.Datetime.from_string(vals.get('date_from', False)) or datetime.max])
        stop = max(self.mapped('date_to') + [fields.Datetime.from_string(vals.get('date_to', False)) or datetime.min])
        employee_ids = self.employee_id.ids
        if 'employee_id' in vals and vals['employee_id']:
            employee_ids += [vals['employee_id']]
        with self.env['hr.work.entry']._error_checking(start=start, stop=stop, skip=skip_check, employee_ids=employee_ids):
            return super().write(vals)

    @api.model_create_multi
    def create(self, vals_list):
        start_dates = [v.get('date_from') for v in vals_list if v.get('date_from')]
        stop_dates = [v.get('date_to') for v in vals_list if v.get('date_to')]
        if any(vals.get('holiday_type', 'employee') == 'employee' and not vals.get('multi_employee', False) and not vals.get('employee_id', False) for vals in vals_list):
            raise ValidationError(_("There is no employee set on the time off. Please make sure you're logged in the correct company."))
        employee_ids = {v['employee_id'] for v in vals_list if v.get('employee_id')}
        with self.env['hr.work.entry']._error_checking(start=min(start_dates, default=False), stop=max(stop_dates, default=False), employee_ids=employee_ids):
            return super().create(vals_list)

    def action_confirm(self):
        start = min(self.mapped('date_from'), default=False)
        stop = max(self.mapped('date_to'), default=False)
        with self.env['hr.work.entry']._error_checking(start=start, stop=stop, employee_ids=self.employee_id.ids):
            return super().action_confirm()

    def _get_leaves_on_public_holiday(self):
        return super()._get_leaves_on_public_holiday().filtered(
            lambda l: l.holiday_status_id.work_entry_type_id.code not in ['LEAVE110', 'LEAVE280'])

    def _validate_leave_request(self):
        super(HrLeave, self)._validate_leave_request()
        self.sudo()._cancel_work_entry_conflict()  # delete preexisting conflicting work_entries
        return True

    def action_refuse(self):
        """
        Override to archive linked work entries and recreate attendance work entries
        where the refused leave was.
        """
        res = super(HrLeave, self).action_refuse()
        self._regen_work_entries()
        return res

    def _action_user_cancel(self, reason):
        res = super()._action_user_cancel(reason)
        self.sudo()._regen_work_entries()
        return res

    def _regen_work_entries(self):
        """
        Called when the leave is refused or cancelled to regenerate the work entries properly for that period.
        """
        work_entries = self.env['hr.work.entry'].sudo().search([('leave_id', 'in', self.ids)])

        work_entries.write({'active': False})
        # Re-create attendance work entries
        vals_list = []
        for work_entry in work_entries:
            vals_list += work_entry.contract_id._get_work_entries_values(work_entry.date_start, work_entry.date_stop)
        self.env['hr.work.entry'].create(vals_list)

    def _get_number_of_days(self, date_from, date_to, employee_id):
        """ If an employee is currently working full time but asks for time off next month
            where he has a new contract working only 3 days/week. This should be taken into
            account when computing the number of days for the leave (2 weeks leave = 6 days).
            Override this method to get number of days according to the contract's calendar
            at the time of the leave.
        """
        days = super(HrLeave, self)._get_number_of_days(date_from, date_to, employee_id)
        if employee_id:
            employee = self.env['hr.employee'].browse(employee_id)
            # Use sudo otherwise base users can't compute number of days
            contracts = employee.sudo()._get_contracts(date_from, date_to, states=['open'])
            contracts |= employee.sudo()._get_incoming_contracts(date_from, date_to)
            calendar = contracts[:1].resource_calendar_id if contracts else None # Note: if len(contracts)>1, the leave creation will crash because of unicity constaint
            # We force the company in the domain as we are more than likely in a compute_sudo
            domain = [('company_id', 'in', self.env.company.ids + self.env.context.get('allowed_company_ids', []))]
            result = employee._get_work_days_data_batch(date_from, date_to, calendar=calendar, domain=domain)[employee.id]
            if self.request_unit_half and result['hours'] > 0:
                result['days'] = 0.5
            return result

        return days

    def _get_calendar(self):
        self.ensure_one()
        if self.date_from and self.date_to:
            contracts = self.employee_id.sudo()._get_contracts(self.date_from, self.date_to, states=['open'])
            contracts |= self.employee_id.sudo()._get_incoming_contracts(self.date_from, self.date_to)
            contract_calendar = contracts[:1].resource_calendar_id if contracts else None
            return contract_calendar or self.employee_id.resource_calendar_id or self.env.company.resource_calendar_id
        return super()._get_calendar()

    def _compute_can_cancel(self):
        super()._compute_can_cancel()

        cancellable_leaves = self.filtered('can_cancel')
        work_entries = self.env['hr.work.entry'].sudo().search([('state', '=', 'validated'), ('leave_id', 'in', cancellable_leaves.ids)])
        leave_ids = work_entries.mapped('leave_id').ids

        for leave in cancellable_leaves:
            leave.can_cancel = leave.id not in leave_ids
