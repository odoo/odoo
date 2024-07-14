# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import csv
import io

from collections import defaultdict
from datetime import date
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class L10nUsW2(models.Model):
    _name = 'l10n.us.w2'
    _description = 'W2 Form'

    @api.model
    def default_get(self, field_list=None):
        if self.env.company.country_id.code != "US":
            raise UserError(_('You must be logged in a US company to use this feature'))
        return super().default_get(field_list)

    date_start = fields.Date("Start Date", default=lambda s: fields.Date.today() + relativedelta(day=1, month=1))
    date_end = fields.Date("End Date", compute='_compute_date_end', store=True, readonly=False)
    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company,
        domain=lambda self: [('id', 'in', self.env.companies.ids)],
        required=True)
    allowed_payslip_ids = fields.Many2many('hr.payslip', compute='_compute_allowed_payslip_ids')
    payslip_ids = fields.Many2many(
        'hr.payslip',
        compute='_compute_payslips_ids',
        store=True,
        readonly=False,
        domain="[('id', 'in', allowed_payslip_ids)]")
    csv_file = fields.Binary("CSV file", readonly=True)
    csv_filename = fields.Char()

    @api.depends('date_start')
    def _compute_date_end(self):
        for w2 in self:
            if not w2.date_start:
                continue
            w2.date_end = date(w2.date_start.year, 12, 31)

    @api.depends('date_end')
    def _compute_display_name(self):
        for w2 in self:
            w2.display_name = f"W-2 Form - {w2.date_end.year}" if w2.date_end else "W-2 Form"

    @api.depends('allowed_payslip_ids')
    def _compute_payslips_ids(self):
        for w2 in self:
            w2.payslip_ids = w2.allowed_payslip_ids

    def _get_allowed_payslips_domain(self):
        self.ensure_one()
        return [
            ('state', 'in', ['done', 'paid']),
            ('date_from', '<=', self.date_end),
            ('date_to', '>=', self.date_start),
            ('company_id', '=', self.company_id.id),
        ]

    @api.depends('company_id', 'date_start', 'date_end')
    def _compute_allowed_payslip_ids(self):
        for w2 in self:
            if not w2.date_start or not w2.date_end or not w2.company_id:
                w2.allowed_payslip_ids = [(5, 0, 0)]
            else:
                allowed_payslips = self.env['hr.payslip'].search(w2._get_allowed_payslips_domain())
                w2.allowed_payslip_ids = allowed_payslips

    def action_generate_csv(self):
        self.ensure_one()
        header = [
            "Employer identification number (EIN)",
            "Employer's name",
            "Street address 1",
            "Street address 2",
            "City or town",
            "State or province",
            "Country",
            "ZIP code",
            "Telephone no.",
            "Email",
            "Employee’s social security number (SSN)",
            "Employee's first name",
            "Employee's  middle initial",
            "Employee's last name",
            "Street address 1",
            "Street address 2",
            "City or town",
            "State or province",
            "Country",
            "ZIP code",
            "Telephone no.",
            "Email",
            "Control number",
            "1 Wages, tips, other compensation",
            "2 Federal income tax withheld",
            "3 Social security wages",
            "4 Social security tax withheld",
            "5 Medicare wages and tips",
            "6 Medicare tax withheld",
            "7 Social security tips",
            "8 Allocated tips",
            "10 Dependent care benefits",
            "11 Nonqualified plans",
            "12a Code A",
            "12a Amount A",
            "12b Code B",
            "12b Amount B",
            "12c Code C",
            "12c Amount C",
            "12d Code D",
            "12d Amount D",
            "13 Statutory employee",
            "13 Retirement plan",
            "13 Third-party sick pay",
            "14 Other A",
            "14 Other amount A",
            "14 Other B",
            "14 Other amount B",
            "14 Other C",
            "14 Other amount C",
            "File directly with state",
            "15 State",
            "15 Employer’s state ID number",
            "16 State wages, tips, etc.",
            "17 State income tax",
            "18 Local wages, tips, etc.",
            "19 Local income tax",
            "20 Locality name",
            "File directly with state",
            "Kind of payer",
            "Kind of employer",
            "Terminating Business",
        ]

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(header)

        payslips_by_employee = defaultdict(lambda: self.env['hr.payslip'])
        for payslip in self.payslip_ids:
            payslips_by_employee[payslip.employee_id] += payslip

        for employee, payslips in payslips_by_employee.items():
            line_values = payslips._get_line_values([
                'TAXABLE', 'FIT', '401K', 'TIPS', 'SST', 'MEDICARE', 'MEDICAREADD', 'ALLOCATEDTIPS',
                'MEDICALFSADC', 'MEDICALHSA', 'ROTH401K',
                'CAINCOMETAX', 'NYINCOMETAX',
                'CASDITAX', 'NYSDITAX',
            ], compute_sum=True)

            writer.writerow([
                self.company_id.vat or "",
                self.company_id.name or "",
                self.company_id.street or "",
                self.company_id.street2 or "",
                self.company_id.city or "",
                self.company_id.state_id.code or "",
                self.company_id.country_id.name or "",
                self.company_id.zip or "",
                self.company_id.phone or "",
                self.company_id.email or "",
                employee.ssnid or "",
                employee.name or "",
                "",
                employee.name or "",
                employee.private_street or "",
                employee.private_street2 or "",
                employee.private_city or "",
                employee.private_state_id.code or "",
                employee.private_country_id.name or "",
                employee.private_zip or "",
                employee.private_phone or "",
                employee.private_email or "",
                "",
                abs(line_values['TAXABLE']['sum']['total']),
                abs(line_values['FIT']['sum']['total']),
                abs(line_values['TAXABLE']['sum']['total'] - line_values['401K']['sum']['total'] - line_values['TIPS']['sum']['total']),
                abs(line_values['SST']['sum']['total']),
                abs(line_values['TAXABLE']['sum']['total'] - line_values['401K']['sum']['total']),
                abs(line_values['MEDICARE']['sum']['total'] + line_values['MEDICAREADD']['sum']['total']),
                abs(line_values['TIPS']['sum']['total']),
                abs(line_values['ALLOCATEDTIPS']['sum']['total']),
                abs(line_values['MEDICALFSADC']['sum']['total']),
                "",
                "D",
                abs(line_values['401K']['sum']['total']),
                "W",
                abs(line_values['MEDICALHSA']['sum']['total']),
                "AA",
                abs(line_values['ROTH401K']['sum']['total']),
                "",
                "",
                "TRUE" if employee.l10n_us_statutory_employee else "FALSE",
                "TRUE" if employee.l10n_us_retirement_plan else "FALSE",
                "TRUE" if employee.l10n_us_third_party_sick_pay else "FALSE",
                _("%s SDI Tax", employee.address_id.state_id.code) if employee.address_id.state_id.code in ['NY', 'CA'] else "",
                abs(line_values['CASDITAX']['sum']['total'] + line_values['NYSDITAX']['sum']['total']),
                "",
                "",
                "",
                "",
                "",
                employee.address_id.state_id.code or "",
                self.company_id.company_registry or "",
                abs(line_values['TAXABLE']['sum']['total']),
                abs(line_values['CAINCOMETAX']['sum']['total'] + line_values['NYINCOMETAX']['sum']['total']),
                "",
                "",
                "",
                "",
                "R",
                "N",
                "",
            ])

        self.csv_file = base64.b64encode(output.getvalue().encode())
        self.csv_filename = f"form_w2_{self.date_end.year}.csv"
