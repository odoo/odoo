# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import defaultdict
import re
from odoo import api, fields, models, _
from ..api.swissdec_declarations import SwissdecDeclaration, SwissdecInstitution
import math
import time


class L10nChSalaryCertificateDeclaration(models.Model):
    _name = 'l10n.ch.salary.certificate'
    _inherit = ['l10n.ch.salary.certificate', 'l10n.ch.swissdec.transmitter']
    _description = 'Tax Salaries Rectification'
    _order = "month desc, year desc"

    previous_declaration = fields.Many2one("ch.yearly.report", domain="[('company_id', '=', company_id), ('l10n_ch_declare_salary_data', '!=', False)]", required=True)
    original_date = fields.Date(required=True)
    tax_rectificate_type = fields.Selection(selection=[("global", "Global Replacement"),
                                                       ("individual", "Individual Replacement")])
    wage_statement_count = fields.Integer(compute="_compute_wage_statement_count")
    tax_rectificate_employee_ids = fields.Many2many("hr.employee", domain="[('company_id', '=', company_id)]")

    def action_prepare_data(self):
        self.ensure_one()
        super().action_prepare_data()
        mapped_certificates = defaultdict()
        persons_to_rectify = False
        if self.tax_rectificate_type == "individual":
            persons_to_rectify = self.tax_rectificate_employee_ids.mapped('registration_number')
        previous_declaration = self.previous_declaration.l10n_ch_declare_salary_data or {}
        previous_staff = previous_declaration.get("Staff", {}).get("Person", [])
        for person in previous_staff:
            if not persons_to_rectify or person.get("Particulars", {}).get("EmployeeNumber") in persons_to_rectify:
                previous_certificates = person.get("TaxSalaries", {}).get("TaxSalary", [])
                if previous_certificates:
                    mapped_certificates[person.get("Particulars", {}).get("EmployeeNumber")] = previous_certificates

        declaration, institutions = self.env["l10n.ch.employee.yearly.values"]._get_salary_rectificates(year=self.previous_declaration.year, month=int(self.previous_declaration.month), company_id=self.company_id, to_replace=mapped_certificates, original_date=self.original_date)
        self.l10n_ch_declare_salary_data = declaration

    def generate_tax_accounting_reports(self):
        self.ensure_one()
        declaration = self._get_declaration()
        report = self.company_id._l10n_ch_swissdec_request(
            route='generate_tax_accounting_report',
            data=declaration,
            is_test=self.test_transmission,
            split_files=False
        )
        report_pdf = report.get("tax_accounting_reports")
        if report_pdf.get('tax_accounting_global.pdf'):
            attachment = self.env['ir.attachment'].create({
                'name': f"Tax_Accounting_Report_{self.year}.pdf",
                'datas': report_pdf.get('tax_accounting_global.pdf'),
                'res_id': self.id,
                'res_model': self._name,
            })
            self.message_post(attachment_ids=[attachment.id])

    def send_tax_accounting_reports(self):
        self.ensure_one()
        declaration = self._get_declaration()

        persons = declaration.get('SalaryDeclaration', {}).get('Company', {}).get("Staff", {}).get('Person', [])
        total_persons = len(persons)
        batch_size = 10
        tax_accounting_reports = {}

        num_batches = math.ceil(total_persons / batch_size)

        for batch_num in range(num_batches):
            start_index = batch_num * batch_size
            end_index = start_index + batch_size

            from_person = start_index + 1
            to_person = min(end_index + 1, total_persons + 1)

            report = self.company_id._l10n_ch_swissdec_request(
                route='generate_tax_accounting_report',
                data=declaration,
                is_test=self.test_transmission,
                from_person=from_person,
                to_person=to_person
            )

            tax_accounting_reports.update(report.get("tax_accounting_reports", {}))

        pattern = re.compile(r"_pers_([A-Za-z0-9_]+)\.pdf$")

        # Let's assume we have employees grouped by registration_number
        employees_mapped_by_registration_number = dict(
            self.env['hr.employee']._read_group(
                domain=[],
                groupby=['registration_number'],
                aggregates=['id:recordset']
            )
        )

        employee_declaration_vals = []

        for file_name, pdf_b64 in tax_accounting_reports.items():

            match = pattern.search(file_name)
            if not match:
                continue
            registration = match.group(1)

            employee = employees_mapped_by_registration_number.get(registration, self.env['hr.employee'])

            if employee:
                employee_declaration_vals.append({
                    'employee_id': employee.id,
                    'res_model': self._name,
                    'res_id': self.id,
                    'pdf_filename': _("Wage_statement_correction_%(year)s_%(name)s_%(timestamp)s", year=self.year, name=employee.name, timestamp=time.time_ns()),
                    'pdf_to_generate': False,
                    'state': 'pdf_generated',
                    'pdf_file': pdf_b64
                })
            else:
                attachment = self.env['ir.attachment'].create({
                    'name': f"Tax_Accounting_Report_{self.year}_{registration}.pdf",
                    'datas': pdf_b64,
                    'res_id': self.id,
                    'res_model': self._name,
                })
                self.message_post(body=_("Employee with number %s was either archived or deleted. Wage statement will not be sent automatically.", registration),attachment_ids=[attachment.id])

        self.env['hr.payroll.employee.declaration'].create(employee_declaration_vals)

    def _compute_wage_statement_count(self):
        mapped_employee_declarations = dict(self.env['hr.payroll.employee.declaration']._read_group(domain=[('res_model', '=', self._name)], groupby=['res_id'], aggregates=['__count']))

        for declaration in self:
            declaration.wage_statement_count = mapped_employee_declarations.get(declaration.id, 0)

    def action_open_wage_statements(self):
        self.ensure_one()
        return {
            'name': _('Wage Statements %s', self.year),
            'res_model': 'hr.payroll.employee.declaration',
            'type': 'ir.actions.act_window',
            'view_mode': 'list,form',
            'domain': [('res_model', '=', self._name), ('res_id', '=', self.id)],
        }


    def _get_institutions(self):
        return [SwissdecInstitution("Tax")]

    def _get_declaration(self):
        self.ensure_one()
        swissdec_declaration = SwissdecDeclaration()
        return swissdec_declaration.create_declare_salary(
            institutions_to_process=self._get_institutions(),
            company_id=self.company_id,
            staff=self.l10n_ch_declare_salary_data,
            declaration_year=self.year,
            test_case=self.test_transmission,
            substitution_declaration_id=self.substituted_declaration_id.swissdec_declaration_id,
            CurrentMonth=(self.year, int(self.month), False)
        )

    def _get_posted_mail_template(self):
        return self.env.ref('documents_hr_payroll.mail_template_new_declaration', raise_if_not_found=False)

    def _get_posted_document_owner(self, employee):
        return employee.user_id
