# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from datetime import datetime, time
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.osv.expression import AND
from odoo.tools import format_date


class HrLeaveType(models.Model):
    _inherit = 'hr.leave.type'

    work_entry_type_id = fields.Many2one('hr.work.entry.type', string='Work Entry Type')


class HrLeave(models.Model):
    _inherit = 'hr.leave'

    def _prepare_resource_leave_vals(self):
        vals = super(HrLeave, self)._prepare_resource_leave_vals()
        vals['work_entry_type_id'] = self.holiday_status_id.work_entry_type_id.id
        return vals

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
                ('date_end', '=', False),
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
            ], ['employee_id'], ['id:recordset'])
            work_entries_by_employee = {
                employee.id: work_entries
                for employee, work_entries in work_entry_groups
            }

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
        skip_check = not bool({'employee_id', 'state', 'request_date_from', 'request_date_to'} & vals.keys())
        employee_ids = self.employee_id.ids
        if 'employee_id' in vals and vals['employee_id']:
            employee_ids += [vals['employee_id']]
        # We check a whole day before and after the interval of the earliest
        # request_date_from and latest request_date_end because date_{from,to}
        # can lie in this range due to time zone reasons.
        # (We can't use date_from and date_to as they are not yet computed at
        # this point.)
        start_dates = self.filtered('request_date_from').mapped('request_date_from') + [fields.Date.to_date(vals.get('request_date_from', False)) or datetime.max.date()]
        stop_dates = self.filtered('request_date_to').mapped('request_date_to') + [fields.Date.to_date(vals.get('request_date_to', False)) or datetime.min.date()]
        start = datetime.combine(min(start_dates) - relativedelta(days=1), time.min)
        stop = datetime.combine(max(stop_dates) + relativedelta(days=1), time.max)
        with self.env['hr.work.entry']._error_checking(start=start, stop=stop, skip=skip_check, employee_ids=employee_ids):
            return super().write(vals)

    @api.model_create_multi
    def create(self, vals_list):
        if any(vals.get('holiday_type', 'employee') == 'employee' and not vals.get('multi_employee', False) and not vals.get('employee_id', False) for vals in vals_list):
            raise ValidationError(_("There is no employee set on the time off. Please make sure you're logged in the correct company."))
        employee_ids = {v['employee_id'] for v in vals_list if v.get('employee_id')}
        # We check a whole day before and after the interval of the earliest
        # request_date_from and latest request_date_end because date_{from,to}
        # can lie in this range due to time zone reasons.
        # (We can't use date_from and date_to as they are not yet computed at
        # this point.)
        start_dates = [fields.Date.to_date(v.get('request_date_from')) for v in vals_list if v.get('request_date_from')]
        stop_dates = [fields.Date.to_date(v.get('request_date_to')) for v in vals_list if v.get('request_date_to')]
        start = datetime.combine(min(start_dates, default=datetime.max.date()) - relativedelta(days=1), time.min)
        stop = datetime.combine(max(stop_dates, default=datetime.min.date()) + relativedelta(days=1), time.max)
        with self.env['hr.work.entry']._error_checking(start=start, stop=stop, employee_ids=employee_ids):
            return super().create(vals_list)

    def action_confirm(self):
        start = min(self.mapped('date_from'), default=False)
        stop = max(self.mapped('date_to'), default=False)
        with self.env['hr.work.entry']._error_checking(start=start, stop=stop, employee_ids=self.employee_id.ids):
            return super().action_confirm()

    def _get_leaves_on_public_holiday(self):
        return super()._get_leaves_on_public_holiday().filtered(
            lambda l: l.holiday_status_id.work_entry_type_id.code not in ['LEAVE110', 'LEAVE210', 'LEAVE280'])

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

    def _compute_can_cancel(self):
        super()._compute_can_cancel()

        cancellable_leaves = self.filtered('can_cancel')
        work_entries = self.env['hr.work.entry'].sudo().search([('state', '=', 'validated'), ('leave_id', 'in', cancellable_leaves.ids)])
        leave_ids = work_entries.mapped('leave_id').ids

        for leave in cancellable_leaves:
            leave.can_cancel = leave.id not in leave_ids
