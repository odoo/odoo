# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta
from collections import defaultdict
from calendar import monthrange

from odoo import api, models, fields
from odoo.tools import format_date


class HrExportWorkEntries(models.TransientModel):
    _name = 'hr.export.work.entries'
    _description = 'Export Work Entries'

    reference_year = fields.Integer(
        string='Year', required=True, default=lambda self: fields.Date.today().year)
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
    ], string='Month', required=True, default=lambda self: str((fields.Date.today()).month))
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True)
    eligible_employee_line_ids = fields.One2many(
        'hr.export.work.entries.employee', 'export_id',
        string='Eligible Employees')
    period_start = fields.Date('Period Start', compute='_compute_period_dates', store=True, readonly=False)
    period_stop = fields.Date('Period Stop', compute='_compute_period_dates', store=True, readonly=False)

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        active_employees = self.env.context.get('active_ids', None)
        period_start, period_stop = self._get_default_period_dates(res)
        lines = self._get_eligible_employee_lines(
            active_employees,
            period_start=period_start,
            period_stop=period_stop,
        )
        res['eligible_employee_line_ids'] = lines
        return res

    def _get_default_period_dates(self, default_values):
        reference_year = default_values.get('reference_year') or fields.Date.today().year
        reference_month = int(default_values.get('reference_month') or fields.Date.today().month)
        period_start = datetime(reference_year, int(reference_month), 1).date()
        period_stop = period_start.replace(
            day=monthrange(reference_year, int(reference_month))[1])
        return period_start, period_stop

    def download_export(self):
        return {
            'name': self.env._('Download Export'),
            'type': 'ir.actions.act_url',
            'url': f'/hr_work_entry/download/{self.env.company.id}/{self.id}',
        }

    def _generate_export_file(self, company_id=None):
        self.ensure_one()
        company = self.env.company if not company_id else self.env['res.company'].browse(company_id)
        file = self._generate_header(company)
        days_in_period = (self.period_stop - self.period_start).days + 1
        for employee_line in self.eligible_employee_line_ids:
            we_by_day_and_code = employee_line._get_work_entries_by_day_and_code()
            for date in (self.period_start + timedelta(days=offset) for offset in range(days_in_period)):
                if we_by_code := we_by_day_and_code.get(date):
                    for work_entry_collection in we_by_code.values():
                        file += self._generate_line(employee_line.employee_id, date, company, work_entry_collection)
        return file.encode()

    def _generate_export_filename(self):
        now = datetime.now()
        formatted_time = format_date(self.env, now).replace('/', '_').replace('.', '_')
        return self.env._('workentries_') + formatted_time

    def _get_columns(self, company):
        columns = [
            (self.env._('Date'), lambda args: format_date(self.env, args['date'])),
            (self.env._('Company'), lambda args: args['company'].name),
            (self.env._('Company External Code'), lambda args: args['company'].external_code or ''),
            (self.env._('Name'), lambda args: args['we_collection']['work_entries'][0]['work_entry_type_id']['name'] or ''),
            (self.env._('Code'), lambda args: args['we_collection']['work_entries'][0]['work_entry_type_id']['code'] or ''),
            (self.env._('External Code'), lambda args: args['we_collection']['work_entries'][0]['work_entry_type_id']['external_code'] or ''),
            (self.env._('Employee Name'), lambda args: args['employee_id'].name),
            (self.env._('Employee Ext. Code'), lambda args: args['employee_id'].external_code or ''),
            (self.env._('Duration'), lambda args: str(round(int(args['we_collection']['duration'] // 3600), 2))),
        ]
        return columns

    def _generate_header(self, company):
        return f"{';'.join(col[0] for col in self._get_columns(company))}\n"

    def _generate_line(self, employee_id, date, company, we_collection=None):
        """
        The export's work entry lines are composed of a series of values. The part in {} is conditionally present

        work_entry.start_date;company.name;company.external_code;work_entry.code;work_entry.name;work_entry.external_code;employee.external_code;employee.name;work_entry.duration
        DATE(DEFAULT FORMAT);CHAR;INT;CHAR;CHAR;INT;CHAR;FLOAT(HOURS)

        eg: 01/05/2026;YourCompany;3434;WORK100;Attendance;1212;5656;Mitchell Admin;8
        """
        columns = self._get_columns(company)
        args = {
            'date': date,
            'employee_id': employee_id,
            'company': company,
            'we_collection': we_collection
        }
        values = [col[1](args) for col in columns]
        line = ';'.join(values)
        return line + '\n'

    def _get_eligible_employee_lines(self, employee_ids=None, period_start=None, period_stop=None):
        """
        To allow for automatic population when specific employees are selected before pressing the Export button,
        there is an employee variable. If it is populated, we only search between those employees.
        When triggering this flow via the default_get (to populate eligible_employee_line_ids during creation)
        self.period_start and self.period_stop are empty, so we leave the possibility of passing them as arguments.
        """
        if period_start is None or period_stop is None:
            period_start = self.period_start
            period_stop = self.period_stop
        contracts_by_employee = self._get_contracts_by_employee(
            employee_ids=employee_ids,
            period_start=period_start,
            period_stop=period_stop,
        )
        lines = [(5, 0, 0)]
        for employee_id, contract_dict in contracts_by_employee.items():
            contracts = self.env['hr.version'].browse([c.id for c in contract_dict.values()])
            work_entries_vals = contracts.generate_work_entries(period_start, period_stop)
            if work_entries_vals:
                lines.append((0, 0, {
                    'employee_id': employee_id,
                    'version_ids': [(6, 0, contracts.ids)],
                }))
        return lines

    def _get_employees(self):
        return self.env['hr.employee'].search(domain=[('company_id', '=', self.env.company.id)])

    def _get_contracts_by_employee(self, employee_ids=None, period_start=None, period_stop=None):
        if employee_ids is None:
            employees = self._get_employees()
        else:
            employees = self.env['hr.employee'].search([('id', '=', employee_ids)])
        if period_start is None or period_stop is None:
            period_start = self.period_start
            period_stop = self.period_stop
        contracts_by_employee = employees._get_contract_versions(date_start=period_start, date_end=period_stop)
        return contracts_by_employee

    @api.depends('reference_year', 'reference_month')
    def _compute_period_dates(self):
        for export in self:
            period_start, period_stop = self._get_default_period_dates({'reference_year': export.reference_year, 'reference_month': export.reference_month})
            export.period_start = period_start
            export.period_stop = period_stop

    @api.depends('period_start')
    def _compute_display_name(self):
        for export in self:
            export.display_name = format_date(self.env, export.period_start, date_format="MMMM y", lang_code=self.env.user.lang)


class HrExportEmployee(models.TransientModel):
    _name = 'hr.export.work.entries.employee'
    _description = 'Work Entry Export Employee'

    export_id = fields.Many2one('hr.export.work.entries', required=True, index=True, ondelete='cascade')
    employee_id = fields.Many2one('hr.employee', required=True, ondelete='cascade', check_company=True)
    version_ids = fields.Many2many('hr.version', compute="_compute_version_ids", store=True, required=True, ondelete='cascade', readonly=False)

    @api.depends('employee_id')
    def _compute_version_ids(self):
        contracts_by_employee = self.export_id._get_contracts_by_employee(employee_ids=self.employee_id)
        for line in self:
            line.version_ids = self.env['hr.version'].browse([c.id for c in contracts_by_employee.get(line.employee_id)])

    def _get_work_entries_by_day_and_code(self, limit_start=None, limit_stop=None):
        """ Group work entries by day and code.

        :param limit_start: Optional start date to limit the split
        :param limit_stop: Optional stop date to limit the split
        :return: A defaultdict {date: defaultdict {code: duration}}}
        """
        self.ensure_one()
        work_entries_by_day_and_code = defaultdict(lambda: defaultdict(lambda: dict(work_entries=[], duration=0)))
        for vals in self.version_ids.generate_work_entries(self.export_id.period_start, self.export_id.period_stop):
            date = vals['date']
            code = vals['work_entry_type_id'].code
            work_entries_by_day_and_code[date][code]['work_entries'].append(vals)
            work_entries_by_day_and_code[date][code]['duration'] += vals['duration'] * 3600
        return work_entries_by_day_and_code
