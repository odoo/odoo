# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import math

from datetime import date
from dateutil.relativedelta import relativedelta
from dateutil.rrule import rrule, DAILY, WEEKLY

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.misc import format_date


class L10nBeExportSDWorxLeavesWizard(models.TransientModel):
    _name = 'l10n_be.export.sdworx.leaves.wizard'
    _description = 'Export Leaves to SDWorx'

    @api.model
    def default_get(self, field_list):
        if self.env.company.country_id.code != "BE":
            raise UserError(_('You must be logged in a Belgian company to use this feature'))
        return super().default_get(field_list)

    def _get_range_of_years(self):
        current_year = fields.Date.today().year
        return [(year, year) for year in range(current_year - 5, current_year + 1)]

    leave_ids = fields.Many2many(
        'hr.leave', string="Leaves", domain=lambda self: [('employee_company_id', '=', self.env.company.id)],
        compute='_compute_leave_ids', store=True, readonly=False)
    reference_year = fields.Selection(
        selection='_get_range_of_years',
        required=True,
        default=lambda self: fields.Date.today().year)
    reference_month = fields.Selection([
        ('1', 'January'),
        ('2', 'February'),
        ('3', 'March'),
        ('4', 'April'),
        ('5', 'May'),
        ('6', 'June'),
        ('7', 'July'),
        ('8', 'August'),
        ('9', 'September'),
        ('10', 'October'),
        ('11', 'November'),
        ('12', 'December'),
    ], required=True, default=lambda self: str((fields.Date.today()).month))
    export_file = fields.Binary('Export File')
    export_filename = fields.Char()

    @api.depends('reference_year', 'reference_month')
    def _compute_leave_ids(self):
        if not self.env.company.sdworx_code:
            raise UserError(_('There is no SDWorx code defined on the company. Please configure it on the Payroll Settings'))
        for wizard in self:
            first_day = date(int(wizard.reference_year), int(wizard.reference_month), 1)
            last_day = first_day + relativedelta(day=31)
            employees = self.env['hr.employee'].search([('company_id', '=', self.env.company.id)])
            invalid_employees = employees.filtered(lambda e: not e.sdworx_code)
            if invalid_employees:
                raise UserError(_('There is no SDWorx code defined for the following employees:\n') + '\n'.join(invalid_employees.mapped('name')))

            leaves = self.env['hr.leave'].search([
                ('employee_id', 'in', employees.ids),
                ('state', '=', 'validate'),
                ('date_to', '>=', first_day),
                ('date_from', '<=', last_day)])
            invalid_work_entry_types = leaves.holiday_status_id.work_entry_type_id.filtered(lambda wet: not wet.sdworx_code)
            if invalid_work_entry_types:
                raise UserError(_('There is no SDWorx code defined for the following work entry types:\n') + '\n'.join(invalid_work_entry_types.mapped('name')))

            wizard.leave_ids = [(6, 0, leaves.ids)]

    def action_generate_export_file(self):
        self.ensure_one()
        def format_duration(amount):
            return str(int(amount * 100)).zfill(4)

        def format_line(employee, day, work_entry_type, duration):
            return "%s%sK%s%s%s" % (
                employee.company_id.sdworx_code,
                employee.sdworx_code,
                day.strftime('%Y%m%d'),
                work_entry_type.sdworx_code,
                duration if isinstance(duration, str) else format_duration(duration))

        work_entry_type_attendance = self.env.ref('hr_work_entry.work_entry_type_attendance')
        current_month = int(self.reference_month)
        first_day = date(int(self.reference_year), current_month, 1)
        last_day = first_day + relativedelta(day=31)
        employees = self.leave_ids.employee_id
        employee_contracts = employees.sudo()._get_contracts(
            first_day, last_day, states=['open', 'close'])
        prestations = {employee: {} for employee in employees}

        for contract in employee_contracts:
            employee = contract.employee_id

            for attendance in contract.resource_calendar_id.attendance_ids:
                if attendance.day_period == "lunch":
                    continue
                start = max(first_day, contract.date_start)
                until = min(last_day, contract.date_end) if contract.date_end else last_day
                if attendance.date_from:
                    start = max(start, attendance.date_from)
                if attendance.date_to:
                    until = min(until, attendance.date_to)
                if attendance.week_type: # Manage even/odd weeks for 2 weeks calendars
                    start_week_type = int(math.floor((start.toordinal() - 1) / 7) % 2)
                    if start_week_type != int(attendance.week_type):
                        # start must be the week of the attendance
                        # if it's not the case, we must remove one week
                        start = start + relativedelta(weeks=-1)
                weekday = int(attendance.dayofweek)
                if attendance.two_weeks_calendar and attendance.week_type:
                    days = rrule(WEEKLY, start, interval=2, until=until, byweekday=weekday)
                else:
                    days = rrule(DAILY, start, until=until, byweekday=weekday)

                for day in days:
                    if day.month != current_month: # Could happen for 2 weeks calendars
                        continue
                    day_char = day.strftime('%Y%m%d')
                    prestation = prestations[employee].get(day_char, {})
                    attendance_duration = attendance.hour_to - attendance.hour_from
                    formatted_line = format_line(
                        employee,
                        day,
                        attendance.work_entry_type_id or work_entry_type_attendance,
                        attendance_duration)
                    prestation['am' if attendance.day_period == 'morning' else 'pm'] = formatted_line
                    prestations[employee][day_char] = prestation

        for leave in self.leave_ids:
            employee = leave.employee_id
            if not leave.request_unit_hours:
                if not leave.request_unit_half:
                    number_of_days = (leave.date_to - leave.date_from).days + 1
                    for i in range(number_of_days):
                        leave_date = leave.date_from + relativedelta(days=i)
                        date_str = leave_date.strftime('%Y%m%d')
                        if date_str in prestations[employee]:
                            prestation = prestations[employee][date_str]
                            if 'am' in prestation:
                                prestation['am'] = format_line(
                                    employee,
                                    leave_date,
                                    leave.holiday_status_id.work_entry_type_id,
                                    prestation['am'][-4:])
                            if 'pm' in prestation:
                                prestation['pm'] = format_line(
                                    employee,
                                    leave_date,
                                    leave.holiday_status_id.work_entry_type_id,
                                    prestation['pm'][-4:])
                else:
                    leave_date = leave.date_from
                    date_str = leave_date.strftime('%Y%m%d')
                    if date_str in prestations[employee]:
                        prestation = prestations[employee][date_str]
                        if leave.request_date_from_period == 'am':
                            prestation['am'] = format_line(
                                employee,
                                leave_date,
                                leave.holiday_status_id.work_entry_type_id,
                                prestation['am'][-4:])
                        else:
                            prestation['pm'] = format_line(
                                employee,
                                leave_date,
                                leave.holiday_status_id.work_entry_type_id,
                                prestation['pm'][-4:])

        prestation_lines = [
            half_day_prestation for employee, employee_prestation in prestations.items() \
                                for day, day_prestation in employee_prestation.items() \
                                for period, half_day_prestation in day_prestation.items()]
        prestation_lines.sort()
        content = '\n'.join(prestation_lines).encode('utf-8')
        self.export_filename = 'SDWorx_export_%s_%s.txt' % (format_date(self.env, first_day, date_format='MMMM'), self.reference_year)
        self.export_file = base64.encodebytes(content)
        return {
            'name': _('Export Work Entries to SDWorx'),
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'view_mode': 'form',
            'res_id': self.id,
            'views': [(False, 'form')],
            'target': 'new',
        }
