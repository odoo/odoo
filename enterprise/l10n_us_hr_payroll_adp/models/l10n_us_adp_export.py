# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import csv
import io
from collections import defaultdict

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.date_utils import start_of, end_of


class L10nUsAdpExport(models.Model):
    _name = 'l10n.us.adp.export'
    _description = 'ADP Export'

    @api.model
    def default_get(self, field_list=None):
        if self.env.company.country_id.code != "US":
            raise UserError(_('You must be logged in a US company to use this feature'))
        return super().default_get(field_list)

    name = fields.Char(compute='_compute_name')
    start_date = fields.Date('Start Date', required=True, default=lambda r: start_of(fields.Date.today(), 'month'))
    end_date = fields.Date('End Date', required=True, default=lambda r: end_of(fields.Date.today(), 'month'))

    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company,
        domain=lambda self: [('id', 'in', self.env.companies.ids)],
        required=True)
    employee_ids = fields.Many2many('hr.employee')
    work_entry_ids = fields.Many2many('hr.work.entry', compute='_compute_work_entry_ids')
    warning_message = fields.Char(compute='_compute_warning_message')
    csv_file = fields.Binary("CSV file", readonly=True)
    csv_filename = fields.Char()
    batch_id = fields.Char("Batch ID",
                           required=True,
                           help="""Batch ID is a unique code that ADP needs when importing Paydata.
                                   We recommend naming it with today's date plus an extra code to ensure a unique value "YYYY-MM-DD-###""")
    batch_description = fields.Char("Batch Description",
                                    help="A short description that will be downloaded in the ADP export to recognize the import batch more easily.")

    @api.depends('batch_id')
    def _compute_name(self):
        for record in self:
            if not record.batch_id:
                record.name = _('ADP Export')
            else:
                record.name = _('ADP Export - %s', record.batch_id)

    def validate_export(self):
        user_error_message = ""

        if not self.company_id.l10n_us_adp_code:
            user_error_message += (_('ADP code is not set for the company.\n'))

        employees_without_adp_code = self.work_entry_ids.mapped('employee_id').filtered(lambda x: not x.l10n_us_adp_code)
        work_entries_types_without_code = [f"{w.name} - {w.code}" for w in self.work_entry_ids.mapped('work_entry_type_id').filtered(lambda x: not x.external_code)]

        if employees_without_adp_code:
            user_error_message += "\n\n"
            user_error_message += _('ADP code is not set for the following employees:\n%s', '\n'.join(employees_without_adp_code.mapped('name')))

        if work_entries_types_without_code:
            user_error_message += "\n\n"
            user_error_message += _('ADP code is not set for the following Work Entries:\n%s', '\n'.join(work_entries_types_without_code))

        if user_error_message:
            raise UserError(user_error_message)

        if not self.work_entry_ids:
            raise UserError(_("No work entries were added for this period."))

    def _get_work_entry_domain(self):
        self.ensure_one()
        return [
            ('date_start', '<=', self.end_date),
            ('date_start', '>=', self.start_date),
            ('company_id', '=', self.company_id.id),
            ('employee_id', 'in', self.employee_ids.ids),
        ]

    @api.depends('company_id', 'start_date', 'end_date', 'employee_ids')
    def _compute_work_entry_ids(self):
        for adp in self:
            allowed_work_entries = self.env['hr.work.entry'].search(adp._get_work_entry_domain())
            adp.work_entry_ids = allowed_work_entries

    @api.depends('work_entry_ids')
    def _compute_warning_message(self):
        for adp in self:
            conflicting_work_entries = adp.work_entry_ids.filtered(lambda x: x.state == 'conflict').employee_id
            if conflicting_work_entries:
                adp.warning_message = _('Warning : Conflicting work entries for the following employees: %s', ','.join(conflicting_work_entries.mapped('name')))
            else:
                adp.warning_message = False

    def _get_grouped_regular_overtime_hours(self, regular_work_entry_type_ids, overtime_work_entry_type_ids):
        self.env.cr.execute(f'''
            SELECT w_e_g.e_id,
            CASE
               WHEN w_e_g.w_e_t_id IN {tuple(regular_work_entry_type_ids)} THEN '_regular'
               WHEN w_e_g.w_e_t_id = {overtime_work_entry_type_ids} THEN '_overtime'
               ELSE w_e_g.external_code
            END
            AS e_code,
            SUM(w_e_g.duration) AS total_hours
            FROM (
                SELECT w_e.employee_id as e_id,
                       w_e.duration as duration,
                       w_e_t.id as w_e_t_id,
                       w_e_t.code as code,
                       w_e_t.external_code as external_code
                FROM hr_work_entry w_e
                LEFT JOIN hr_work_entry_type w_e_t
                ON w_e.work_entry_type_id=w_e_t.id
                WHERE w_e.id IN {tuple(self.work_entry_ids.ids)}
            ) w_e_g
            GROUP BY
                w_e_g.e_id,
                e_code
            ORDER BY 
                w_e_g.e_id,
                e_code
        ''')

        return self.env.cr.dictfetchall()

    def _generate_rows(self):
        co_code = self.company_id.l10n_us_adp_code
        batch_id = self.batch_id or ""
        batch_description = self.batch_description or ""

        regular_work_entries = self.env.ref('hr_work_entry.work_entry_type_attendance')
        regular_work_entries |= self.env.ref('hr_work_entry_contract.work_entry_type_home_working')
        overtime_work_entries = self.env.ref('hr_work_entry.overtime_work_entry_type')

        grouped_work_entries = self._get_grouped_regular_overtime_hours(regular_work_entries.ids, overtime_work_entries.id)

        employee_info = defaultdict(lambda: {'Rate': 0, 'is_monthly': False,
                                             'Employee Name': '',
                                             'File  #': '',
                                             'Co Code': co_code,
                                             'Batch ID': batch_id,
                                             'Batch Description': batch_description,
                                             'total_business_hours': 0,
                                             'Regular Hours': 0,
                                             'Regular Earnings': 0,
                                             'Overtime Hours': 0,
                                             'Overtime Earnings': 0})

        employees = self.work_entry_ids.mapped('employee_id')

        for emp in employees:
            employee_info[emp.id]['Rate'] = emp.contract_id.hourly_wage if emp.contract_id.wage_type == 'hourly' else emp.contract_id.wage
            employee_info[emp.id]['is_monthly'] = emp.contract_id.wage_type == 'monthly'
            employee_info[emp.id]['Employee Name'] = emp.name
            employee_info[emp.id]['File  #'] = emp.l10n_us_adp_code

        work_entry_info = defaultdict(lambda: {
            "code_name": '',
            "hours_name": '',
            "earning_name": ''
        })

        for row in grouped_work_entries:
            employee_info[row["e_id"]]["total_business_hours"] += row["total_hours"]

        for row in grouped_work_entries:
            if row['e_code'] == "_regular":
                employee_info[row['e_id']]["Regular Hours"] = round(row["total_hours"], 2)
                if employee_info[row['e_id']]['is_monthly']:
                    employee_info[row['e_id']]["Regular Earnings"] = round((row["total_hours"] * employee_info[row['e_id']]['Rate']) / employee_info[row["e_id"]]["total_business_hours"], 2)

            elif row['e_code'] == "_overtime":
                employee_info[row['e_id']]["Overtime Hours"] = round(row["total_hours"], 2)
                if employee_info[row['e_id']]['is_monthly']:
                    employee_info[row['e_id']]["Overtime Earnings"] = round((row["total_hours"] * employee_info[row['e_id']]['Rate'] * 1.5) / employee_info[row["e_id"]]["total_business_hours"], 2)
            else:
                if row['e_code'] not in work_entry_info:
                    work_entry_type = self.work_entry_ids.filtered(lambda w: w.external_code == row['e_code']).work_entry_type_id
                    work_entry_info[row["e_code"]] = {
                        "code_name": f"{work_entry_type.name} {row['e_code']}",
                        "hours_name": f"{work_entry_type.name} Hours-{row['e_code']}",
                        "earning_name": f"{work_entry_type.name} Earnings-{row['e_code']}"
                    }
                employee_info[row['e_id']][work_entry_info.get(row['e_code'])['hours_name']] = round(row['total_hours'], 2)
                employee_info[row['e_id']][work_entry_info.get(row['e_code'])['code_name']] = row['e_code']
                if employee_info[row['e_id']]['is_monthly']:
                    employee_info[row['e_id']][work_entry_info.get(row['e_code'])['earning_name']] = round((row['total_hours'] * employee_info[row['e_id']]['Rate']) / employee_info[row["e_id"]]["total_business_hours"], 2)

        header = [
            "Co Code",
            "Batch ID",
            "File  #",
            "Employee Name",
            "Batch Description",
            "Rate",
            "Regular Hours",
            "Regular Earnings",
            "Overtime Hours",
            "Overtime Earnings",
        ]

        for w_e in work_entry_info.values():
            header += [w_e['code_name'], w_e['hours_name'], w_e['earning_name']]

        return [header] + [[emp.get(row_name, '') for row_name in header] for emp in employee_info.values()]

    def action_generate_csv(self):
        self.ensure_one()
        self.validate_export()


        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerows(self._generate_rows())

        self.csv_file = base64.b64encode(output.getvalue().encode())
        company_code_formatted = f"{self.company_id.l10n_us_adp_code:3}".replace(' ', '_')
        self.csv_filename = f"EPI{company_code_formatted}{self.end_date.month:02}.csv"

    def action_open_work_entries(self):
        self.ensure_one()
        return {
            'name': _('Exported Work Entries'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.work.entry',
            'view_ids': [(False, 'gantt')],
            'view_mode': 'gantt',
            'domain': [('id', 'in', self.work_entry_ids.ids)]
        }
