# Part of Odoo. See LICENSE file for full copyright and licensing details.

from base64 import b64encode
from datetime import datetime, time, timedelta
from calendar import monthrange
from collections import defaultdict
from dataclasses import dataclass
from typing import NamedTuple

from odoo import api, fields, models
from odoo.exceptions import RedirectWarning, UserError, ValidationError
from odoo.osv.expression import AND, OR
from odoo.tools import format_date


class SplittedWorkEntry(NamedTuple):
    start: datetime
    stop: datetime
    work_entry: models.Model


@dataclass
class WorkEntryCollection:
    work_entries: models.Model
    duration: int


class HrWorkEntryExportMixin(models.AbstractModel):
    _name = 'hr.work.entry.export.mixin'
    _description = 'Work Entry Export Mixin'

    @api.model
    def _country_restriction(self):
        return False

    @api.model
    def default_get(self, field_list=None):
        country_restriction = self._country_restriction()
        if country_restriction and country_restriction not in self.env.companies.mapped('country_id.code'):
            raise UserError(self.env._(
                'You must be logged in a %(country_code)s company to use this feature',
                country_code=country_restriction
            ))
        return super().default_get(field_list)

    def _get_company_domain(self):
        domain = [('id', 'in', self.env.companies.ids)]
        if restriction := self._country_restriction():
            domain = AND([domain, [('partner_id.country_id.code', '=', restriction)]])
        return domain

    create_uid = fields.Many2one('res.users', index=True)
    reference_year = fields.Integer(
        'Reference Year', required=True, default=lambda self: fields.Date.today().year)
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
    eligible_employee_line_ids = fields.One2many(
        'hr.work.entry.export.employee.mixin', 'export_id',
        string='Eligible Employees')
    eligible_employee_count = fields.Integer(
        'Eligible Employees Count', compute='_compute_eligible_employee_count')
    period_start = fields.Date('Period Start', compute='_compute_period_dates', store=True)
    period_stop = fields.Date('Period Stop', compute='_compute_period_dates', store=True)
    export_file = fields.Binary('Export File', readonly=True)
    export_filename = fields.Char('Export Filename', readonly=True)
    company_id = fields.Many2one(
        'res.company', domain=lambda self: self._get_company_domain(),
        default=lambda self: self.env.company, required=True)

    @api.depends('period_start')
    def _compute_display_name(self):
        for export in self:
            export.display_name = format_date(self.env, export.period_start, date_format="MMMM y", lang_code=self.env.user.lang)

    @api.depends('reference_year', 'reference_month')
    def _compute_period_dates(self):
        for export in self:
            export.period_start = datetime(export.reference_year, int(export.reference_month), 1).date()
            export.period_stop = export.period_start.replace(
                day=monthrange(export.reference_year, int(export.reference_month))[1])

    @api.depends('eligible_employee_line_ids')
    def _compute_eligible_employee_count(self):
        for export in self:
            export.eligible_employee_line_ids.filtered(lambda line: not line.work_entry_ids or not line.contract_ids).unlink()
            export.eligible_employee_count = len(export.eligible_employee_line_ids)

    @api.model
    def _get_authorized_employee_types(self):
        return ['employee', 'worker']

    def _get_employee_ids(self):
        return self.env['hr.employee']._search(
            domain=AND([
                [('company_id', '=', self.company_id.id)],
                [('employee_type', 'in', self._get_authorized_employee_types())],
            ]),
        )

    def _get_relevant_work_entries_by_employee(self, employee_ids=None):
        if employee_ids is None:
            employee_ids = self._get_employee_ids()
        relevant_work_entries_by_employee = dict(self.env['hr.work.entry']._read_group(
            domain=[
                ('employee_id', 'in', employee_ids),
                ('date_start', '<=', self.period_stop),
                ('date_stop', '>=', self.period_start),
                ('state', 'in', ['draft', 'validated', 'conflict']),
            ],
            groupby=['employee_id'],
            aggregates=['id:recordset'],
        ))
        return relevant_work_entries_by_employee

    def _get_contracts_by_employee(self, employee_ids=None):
        if employee_ids is None:
            employee_ids = self._get_employee_ids()
        contracts_by_employee = dict(self.env['hr.contract']._read_group(
            domain=[
                ('employee_id', 'in', employee_ids),
                ('date_start', '<=', self.period_stop),
                ('state', 'in', ['open', 'close']),
                '|',
                    ('date_end', '>=', self.period_start),
                    ('date_end', '=', False),
            ],
            groupby=['employee_id'],
            aggregates=['id:recordset'],
        ))
        return contracts_by_employee

    def _generate_export_file(self):
        raise NotImplementedError()

    def _generate_export_filename(self):
        raise NotImplementedError()

    def _get_name(self):
        return self.env._('Work Entries Export')

    def _get_view_ref(self):
        return 'hr_payroll.hr_work_entry_export_mixin_form_view'

    def action_export_file(self):
        self.ensure_one()
        self.eligible_employee_line_ids._check_data()
        self.eligible_employee_line_ids._check_work_entries()
        self.export_file = b64encode(self._generate_export_file().encode())
        self.export_filename = self._generate_export_filename()
        return {
            'name': self._get_name(),
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'views': [(self.env.ref(self._get_view_ref()).id, 'form')],
        }

    def action_populate(self):
        self.ensure_one()
        contracts_by_employee = self._get_contracts_by_employee()
        relevant_work_entries_by_employee = self._get_relevant_work_entries_by_employee()
        lines = [(5, 0, 0)]
        for employee, contracts in contracts_by_employee.items():
            if relevant_work_entries_by_employee.get(employee):
                lines.append((0, 0, {
                    'export_id': self.id,
                    'employee_id': employee.id,
                    'contract_ids': [(6, 0, contracts.ids)],
                }))
        self.eligible_employee_line_ids = lines
        return {
            'name': self._get_name(),
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'views': [(self.env.ref(self._get_view_ref()).id, 'form')],
        }

    def action_open_employees(self):
        self.ensure_one()
        return {
            'name': self.env._('Eligible Employees'),
            'res_model': self.eligible_employee_line_ids._name,
            'domain': [('id', 'in', self.eligible_employee_line_ids.ids)],
            'context': {'default_export_id': self.id},
            'type': 'ir.actions.act_window',
            'view_mode': 'list',
        }


class HrWorkEntryExportEmployeeMixin(models.AbstractModel):
    _name = 'hr.work.entry.export.employee.mixin'
    _description = 'Work Entry Export Employee'

    export_id = fields.Many2one('hr.work.entry.export.mixin', required=True, ondelete='cascade')
    employee_id = fields.Many2one('hr.employee', required=True, ondelete='cascade')
    contract_ids = fields.Many2many('hr.contract', compute="_compute_contract_ids", store=True, required=True, ondelete='cascade', readonly=False)
    work_entry_ids = fields.Many2many('hr.work.entry', compute='_compute_work_entry_ids')

    @api.depends('employee_id')
    def _compute_contract_ids(self):
        contracts_by_employee = self.export_id._get_contracts_by_employee(employee_ids=self.employee_id.ids)
        for line in self:
            line.contract_ids = contracts_by_employee.get(line.employee_id)

    @api.depends('export_id.period_start', 'export_id.period_stop', 'employee_id')
    def _compute_work_entry_ids(self):
        lines_by_export = defaultdict(lambda: self.env[self._name])
        for line in self:
            lines_by_export[line.export_id] += line
        for export, lines in lines_by_export.items():
            relevant_work_entries_by_employee = export._get_relevant_work_entries_by_employee(employee_ids=lines.employee_id.ids)
            for line in lines:
                line.work_entry_ids = relevant_work_entries_by_employee.get(line.employee_id)

    def _relations_to_check(self):
        """
        To be overridden in order to check for missing data in related fields.
        example:
        ```py
        def _relations_to_check(self):
             relations = super()._relations_to_check()
             return relations + ['employee_id.group_s_code']
        ```

        :return: A list of the field to check in dot notation
        """
        return []

    def _check_data(self):
        def explore_and_check(path):
            base_record_path, field = path.rsplit('.', maxsplit=1)
            base_records = self.mapped(base_record_path)
            return base_records.filtered(lambda r: not r[field])

        messages = []
        for model_display_name, field_chain in self._relations_to_check():
            if problematic_records := explore_and_check(field_chain):
                final_field_name = field_chain.rsplit('.', maxsplit=1)[-1]
                field_display_name = problematic_records._fields[final_field_name].string
                record_names = '\n    • '.join(problematic_records.mapped('name'))

                message = self.env._(
                    "The following %(model_name)s are missing a %(field_name)s:\n    • %(names)s",
                    model_name=model_display_name,
                    field_name=field_display_name,
                    names=record_names
                )
                messages.append(message)

        if messages:
            raise ValidationError('\n\n'.join(messages))

    def _split_work_entries_on_midnight(self, limit_start=None, limit_stop=None):
        """ Split work entries that span multiple days into multiple work entries that each span a single day.
        the work entries are sorted by date_start given _order of hr.work.entry

        :param limit_start: Optional start date to limit the split
        :param limit_stop: Optional stop date to limit the split
        :return: A list of SplittedWorkEntry(start, stop, work_entry) (pseudo record set)
        """
        self.ensure_one()
        splitted_work_entries = []
        for work_entry in self.work_entry_ids:
            start = max(work_entry.date_start, datetime.combine(limit_start, time.min)) \
                if limit_start else work_entry.date_start
            stop = min(work_entry.date_stop, datetime.combine(limit_stop, time.max)) \
                if limit_stop else work_entry.date_stop

            if start.date() == stop.date():
                splitted_work_entries.append(SplittedWorkEntry(start, stop, work_entry))
                continue

            midnight_after_start = datetime.combine(start.date() + timedelta(days=1), time.min)
            splitted_work_entries.append(SplittedWorkEntry(midnight_after_start, stop, work_entry))

            current_start = datetime.combine(start.date(), time.min) + timedelta(days=1)
            day_before_stop = datetime.combine(stop.date() - timedelta(days=1), time.max)
            while current_start < day_before_stop:
                next_midnight = datetime.combine(current_start, time.max)
                splitted_work_entries.append(SplittedWorkEntry(next_midnight, next_midnight, work_entry))
                current_start += timedelta(days=1)

            splitted_work_entries.append(SplittedWorkEntry(current_start, stop, work_entry))
        return splitted_work_entries

    def _get_work_entries_by_day_and_code(self, limit_start=None, limit_stop=None):
        """ Group work entries by day and code.

        :param limit_start: Optional start date to limit the split
        :param limit_stop: Optional stop date to limit the split
        :return: A defaultdict {date: defaultdict {code: WorkEntryCollection {work_entries, duration}}}
        """
        self.ensure_one()
        work_entry_intervals = self._split_work_entries_on_midnight(limit_start, limit_stop)
        work_entries_by_day_and_code = defaultdict(lambda: defaultdict(lambda: WorkEntryCollection(
            work_entries=self.env['hr.work.entry'],
            duration=0,
        )))
        for work_entry_interval in work_entry_intervals:
            date = work_entry_interval.start.date()
            code = work_entry_interval.work_entry.work_entry_type_id.code
            work_entries_by_day_and_code[date][code].work_entries |= work_entry_interval.work_entry
            work_entries_by_day_and_code[date][code].duration += (
                work_entry_interval.stop - work_entry_interval.start).total_seconds()
        return work_entries_by_day_and_code

    def _check_work_entries(self):
        if any(work_entry.state == 'conflict' for work_entry in self.work_entry_ids):
            base_domain = [
                ('employee_id', 'in', self.employee_id.ids),
                ('state', '=', 'conflict'),
            ]
            time_domain = OR([[
                ('date_start', '>=', datetime.combine(export.period_start, time.min)),
                ('date_start', '<=', datetime.combine(export.period_stop, time.max)),
            ] for export in self.export_id])

            raise RedirectWarning(
                message=self.env._('Some work entries are in conflict. Please resolve the conflicts before exporting.'),
                action=self.env.ref('hr_work_entry.hr_work_entry_action_conflict').id,
                button_text=self.env._('Resolve Conflicts'),
                additional_context={'domain': AND([base_domain, time_domain])}
            )

    def action_open_work_entries(self):
        self.ensure_one()
        return {
            'name': self.env._('Work Entries for %(employee)s', employee=self.employee_id.name),
            'res_model': self.work_entry_ids._name,
            'type': 'ir.actions.act_window',
            'view_mode': 'gantt,calendar,list,pivot,form',
            'domain': [('id', 'in', self.work_entry_ids.ids)],
        }
