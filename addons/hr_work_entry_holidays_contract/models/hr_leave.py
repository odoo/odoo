# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, date

from odoo import api, models, _
from odoo.exceptions import ValidationError

class HrLeave(models.Model):
    _inherit = 'hr.leave'

    def _get_new_resource_leave_values(self):
        """
        This method override the default behavior to generate new resource values depending on employee contract.
        :return: resource_leave_values to be created by _create_resource_leave
        """
        self.ensure_one()
        contract = self.employee_id.sudo()._get_contracts(self.date_from, self.date_to, states=['open'])
        if contract and contract.resource_calendar_id != self.employee_id.resource_calendar_id:
            return[{
                'name': self.name,
                'holiday_id': self.id,
                'resource_id': self.employee_id.resource_id.id,
                'work_entry_type_id': self.holiday_status_id.work_entry_type_id.id,
                'time_type': self.holiday_status_id.time_type,
                'date_from': max(self.date_from, datetime.combine(contract.date_start, datetime.min.time())),
                'date_to': min(self.date_to, datetime.combine(contract.date_end or date.max, datetime.max.time())),
                'calendar_id': contract.resource_calendar_id.id,
            }]

    @api.constrains('date_from', 'date_to')
    def _check_contracts(self):
        """
            A leave cannot be set across multiple contracts.
            Note: a leave can be across multiple contracts despite this constraint.
            It happens if a leave is correctly created (not accross multiple contracts) but
            contracts are later modifed/created in the middle of the leave.
        """
        for holiday in self.filtered('employee_id'):
            domain = [
                ('employee_id', '=', holiday.employee_id.id),
                ('date_start', '<=', holiday.date_to),
                '|',
                ('state', 'not in', ['draft', 'cancel']),
                '&',
                ('state', '=', 'draft'),
                ('kanban_state', '=', 'done'),
                '|',
                    ('date_end', '>=', holiday.date_from),
                    '&',
                        ('date_end', '=', False),
                        ('state', '!=', 'close')
            ]
            nbr_contracts = self.env['hr.contract'].sudo().search_count(domain)
            if nbr_contracts > 1:
                contracts = self.env['hr.contract'].sudo().search(domain)
                raise ValidationError(_('A leave cannot be set across multiple contracts.') + '\n' + ', '.join(contracts.mapped('name')))

    def _get_work_entry_values(self):
        """
        This method return work-entry values based on the leave values.
        :return: work entry list of new values.
        """
        # overriden to take into account of generated contracts work entries.
        work_entries_vals_list = []
        for leave in self:
            contracts = leave.employee_id.sudo()._get_contracts(leave.date_from, leave.date_to, states=['open', 'close'])
            for contract in contracts:
                # Generate only if it has already been generated
                if leave.date_to >= contract.date_generated_from and leave.date_from <= contract.date_generated_to:
                    work_entries_vals_list += contracts._get_work_entries_values(leave.date_from, leave.date_to)
        return work_entries_vals_list

    def _get_work_entry_to_intervals(self, work_entry):
        """
        work_entry are overriden in hr_work_entry_contract therefore, the  _to_intervals method is available
        :param work_entry:
        :return:
        """
        return work_entry._to_intervals()

    def _refused_work_entry(self, work_entries):
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
            return employee._get_work_days_data_batch(date_from, date_to, calendar=calendar)[employee.id]

        return days

    def _get_calendar(self):
        self.ensure_one()
        if self.date_from and self.date_to:
            contracts = self.employee_id.sudo()._get_contracts(self.date_from, self.date_to, states=['open'])
            contracts |= self.employee_id.sudo()._get_incoming_contracts(self.date_from, self.date_to)
            contract_calendar = contracts[:1].resource_calendar_id if contracts else None
            return contract_calendar or self.employee_id.resource_calendar_id or self.env.company.resource_calendar_id
        return super()._get_calendar()
