# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import defaultdict
from itertools import groupby
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import timedelta
from dateutil.relativedelta import relativedelta


class HrWorkEntryRegenerationWizard(models.TransientModel):
    _name = 'hr.work.entry.regeneration.wizard'
    _description = 'Regenerate Employee Work Entries'

    earliest_available_date = fields.Date('Earliest date', compute='_compute_earliest_available_date')
    earliest_available_date_message = fields.Char(readonly=True, store=False, default='')
    latest_available_date = fields.Date('Latest date', compute='_compute_latest_available_date')
    latest_available_date_message = fields.Char(readonly=True, store=False, default='')
    date_from = fields.Date('From', required=True, default=lambda self: self.env.context.get('date_start'))
    date_to = fields.Date('To', required=True, compute='_compute_date_to', store=True,
            readonly=False, default=lambda self: self.env.context.get('date_end'))
    employee_ids = fields.Many2many('hr.employee', string='Employees',
                                    domain=lambda self: [('company_id', 'in', self.env.companies.ids)], required=True)
    validated_work_entry_employee_ids = fields.Many2many('hr.employee', export_string_translation=False,
                                   compute='_compute_validated_work_entry_employee_ids')
    search_criteria_completed = fields.Boolean(compute='_compute_search_criteria_completed')
    valid = fields.Boolean(compute='_compute_valid')

    @api.depends('date_from')
    def _compute_date_to(self):
        for wizard in self:
            wizard.date_to = wizard.date_from and wizard.date_from + relativedelta(months=+1, day=1, days=-1)

    @api.depends('employee_ids')
    def _compute_earliest_available_date(self):
        for wizard in self:
            dates = wizard.employee_ids.version_ids.mapped('date_generated_from')
            wizard.earliest_available_date = min(dates) if dates else None

    @api.depends('employee_ids')
    def _compute_latest_available_date(self):
        for wizard in self:
            dates = wizard.employee_ids.version_ids.mapped('date_generated_to')
            wizard.latest_available_date = max(dates) if dates else None

    @api.depends('date_from', 'date_to', 'employee_ids')
    def _compute_validated_work_entry_employee_ids(self):
        for wizard in self:
            employee_ids = self.env['hr.employee']
            if wizard.search_criteria_completed:
                validated_work_entry_by_employee = self.env['hr.work.entry']._read_group([
                    ('employee_id', 'in', wizard.employee_ids.ids),
                    ('date', '>=', wizard.date_from),
                    ('date', '<=', wizard.date_to),
                    ('state', '=', 'validated')
                ], ['employee_id'])
                for per_employee in validated_work_entry_by_employee:
                    employee_ids |= per_employee[0]
            wizard.validated_work_entry_employee_ids = employee_ids

    @api.depends('validated_work_entry_employee_ids', 'employee_ids')
    def _compute_valid(self):
        for wizard in self:
            wizard.valid = wizard.search_criteria_completed and len(wizard.employee_ids - wizard.validated_work_entry_employee_ids) > 0

    @api.depends('date_from', 'date_to', 'employee_ids')
    def _compute_search_criteria_completed(self):
        for wizard in self:
            wizard.search_criteria_completed = wizard.date_from and wizard.date_to and wizard.employee_ids and wizard.earliest_available_date and wizard.latest_available_date

    @api.onchange('date_from', 'date_to', 'employee_ids')
    def _check_dates(self):
        for wizard in self:
            wizard.earliest_available_date_message = ''
            wizard.latest_available_date_message = ''
            if wizard.search_criteria_completed:
                if wizard.date_from > wizard.date_to:
                    date_from = wizard.date_from
                    wizard.date_from = wizard.date_to
                    wizard.date_to = date_from
                if wizard.earliest_available_date and wizard.date_from < wizard.earliest_available_date:
                    wizard.date_from = wizard.earliest_available_date
                    wizard.earliest_available_date_message = f'The earliest available date is {self._date_to_string(wizard.earliest_available_date)}'
                if wizard.latest_available_date and wizard.date_to > wizard.latest_available_date:
                    wizard.date_to = wizard.latest_available_date
                    wizard.latest_available_date_message = f'The latest available date is {self._date_to_string(wizard.latest_available_date)}'

    @api.model
    def _date_to_string(self, date):
        if not date:
            return ''
        user_date_format = self.env['res.lang']._get_data(code=self.env.user.lang).date_format
        return date.strftime(user_date_format)

    def _work_entry_fields_to_nullify(self):
        return ['active']

    def regenerate_work_entries(self, slots=None, record_ids=None):
        write_vals = {field: False for field in self._work_entry_fields_to_nullify()}
        if not slots:
            if not self.env.context.get('work_entry_skip_validation'):
                if not self.search_criteria_completed:
                    raise ValidationError(_("In order to regenerate the work entries, you need to provide the wizard with an employee_id, a date_from and a date_to."))

                if self.date_from < self.earliest_available_date or self.date_to > self.latest_available_date:
                    raise ValidationError(_("The from date must be >= '%(earliest_available_date)s' and the to date must be <= '%(latest_available_date)s', which correspond to the generated work entries time interval.", earliest_available_date=self._date_to_string(self.earliest_available_date), latest_available_date=self._date_to_string(self.latest_available_date)))

                if not self.valid:
                    raise ValidationError(self.env._("No work entry can be regenerated in this range of dates and these employees."))

            valid_employees = self.employee_ids - self.validated_work_entry_employee_ids
            date_from = max(self.date_from, self.earliest_available_date) if self.earliest_available_date else self.date_from
            date_to = min(self.date_to, self.latest_available_date) if self.latest_available_date else self.date_to
            work_entries = self.env['hr.work.entry'].search([
                ('employee_id', 'in', valid_employees.ids),
                ('date', '>=', date_from),
                ('date', '<=', date_to),
                ('state', '!=', 'validated')])
            work_entries.write(write_vals)
            valid_employees.generate_work_entries(date_from, date_to, True)
        else:
            range_by_employee = defaultdict(list)
            slots.sort(key=lambda d: (d['employee_id'], d['date']))
            for employee_id, records in groupby(slots, lambda d: d['employee_id']):
                dates = [fields.Date.from_string(r['date']) for r in records]
                start = end = dates[0]
                for current in dates[1:]:
                    if current - end != timedelta(days=1):
                        range_by_employee[start, end].append(employee_id)
                        start = current
                    end = current
                range_by_employee[start, end].append(employee_id)
            work_entries = self.env['hr.work.entry'].browse(record_ids)
            work_entries.write(write_vals)
            for (date_from, date_to), employee_ids in range_by_employee.items():
                valid_employees = self.env["hr.employee"].browse(employee_ids)
                valid_employees.generate_work_entries(date_from, date_to, True)
