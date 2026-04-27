# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from ..api.swissdec_declarations import SwissdecDeclaration, SwissdecInstitution
import re
import base64
import math
import time


class L10nCHInsuranceReport(models.Model):
    _name = 'ch.yearly.report'
    _inherit = ['ch.yearly.report', 'l10n.ch.swissdec.transmitter']

    incomplete_declaration = fields.Boolean()
    tax_cross_border_institutions = fields.Many2many('l10n.ch.source.tax.institution')
    tax_certificates = fields.Boolean()
    wage_statement_count = fields.Integer(compute="_compute_wage_statement_count")

    def _compute_actionable_warnings(self):
        super()._compute_actionable_warnings()
        for declaration in self:
            actionable_warnings = declaration.actionable_warnings or {}
            i = 0
            if declaration.l10n_ch_declare_salary_data:
                for person in declaration.l10n_ch_declare_salary_data["Staff"]["Person"]:
                    if "AHV-AVS-Salaries" in person:
                        for salary_object in person["AHV-AVS-Salaries"]["AHV-AVS-Salary"]:
                            avs_salary = float(salary_object.get("AHV-AVS-Income", "0.00"))
                            if avs_salary < 0 and "AHV-AVS-IncomeSplits" not in salary_object:
                                actionable_warnings[f"negative_avs_{i}"] = {
                                    'message': f"{person['Particulars']['Firstname']} {person['Particulars']['Lastname']} has negative AVS-Salary of {avs_salary} for this year, a split or an additional delivery date is required",
                                    'action': self.env['l10n.ch.avs.splits']._get_records_action(name=_("New OASI Split"), context={
                                        "default_employee_id": self.env['hr.employee'].search([('registration_number', '=', person['Particulars'].get("EmployeeNumber", False))], limit=1).id,
                                        "default_year": declaration.year,
                                        "default_income_to_split": avs_salary
                                    }),
                                    'level': "warning",
                                    "action_text": _("Split AVS Salary"),
                                }
                                i += 1
            declaration.actionable_warnings = actionable_warnings

    def action_prepare_data(self):
        self.ensure_one()
        super().action_prepare_data()
        declaration, institutions = self.env["l10n.ch.employee.yearly.values"]._get_yearly_retrospective(year=self.year, month=int(self.month), company_id=self.company_id, incomplete_declaration=self.incomplete_declaration)
        self.l10n_ch_declare_salary_data = declaration
        self.avs_institution_ids = self.env['l10n.ch.social.insurance'].browse(institutions.get("AVS", []))
        self.caf_institution_ids = self.env['l10n.ch.compensation.fund'].browse(institutions.get("CAF", []))
        self.laa_institution_ids = self.env['l10n.ch.accident.insurance'].browse(institutions.get("LAA", []))
        self.laac_institution_ids = self.env['l10n.ch.additional.accident.insurance'].browse(institutions.get("LAAC", []))
        self.ijm_institution_ids = self.env['l10n.ch.sickness.insurance'].browse(institutions.get("IJM", []))
        self.tax_cross_border_institutions = self.env['l10n.ch.source.tax.institution'].browse(institutions.get("TXB", []))
        self.tax_certificates = institutions.get("Tax", False)


    def _get_institutions(self):
        institutions = list(self.avs_institution_ids) + list(self.caf_institution_ids) + list(self.laa_institution_ids) + list(self.laac_institution_ids) + list(self.ijm_institution_ids) + list(self.tax_cross_border_institutions)
        if self.tax_certificates:
            institutions += [SwissdecInstitution("Tax")]
        return institutions

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

    def generate_ahv_report(self):
        self.ensure_one()
        declaration = self._get_declaration()
        report = self.company_id._l10n_ch_swissdec_request(
            route='generate_report',
            data=declaration,
            is_test=self.test_transmission,
            report_type="AhvReport"
        )
        report_pdf = report.get("AhvReport")
        if report_pdf:
            attachment = self.env['ir.attachment'].create({
                'name': f"AVS_Report_{self.year}.pdf",
                'datas': report_pdf,  # Must be base64-encoded already
                'res_id': self.id,
                'res_model': self._name,
            })
            self.message_post(attachment_ids=[attachment.id])

    def generate_free_ahv_report(self):
        self.ensure_one()
        declaration = self._get_declaration()
        report = self.company_id._l10n_ch_swissdec_request(
            route='generate_report',
            data=declaration,
            is_test=self.test_transmission,
            report_type="AhvFreeReport"
        )
        report_pdf = report.get("AhvFreeReport")
        if report_pdf:
            attachment = self.env['ir.attachment'].create({
                'name': f"AVS_Free_Report_{self.year}.pdf",
                'datas': report_pdf,
                'res_id': self.id,
                'res_model': self._name,
            })
            self.message_post(attachment_ids=[attachment.id])

    def generate_fak_report(self):
        self.ensure_one()
        declaration = self._get_declaration()
        report = self.company_id._l10n_ch_swissdec_request(
            route='generate_report',
            data=declaration,
            is_test=self.test_transmission,
            report_type="FakReport"
        )
        report_pdf = report.get("FakReport")
        if report_pdf:
            attachment = self.env['ir.attachment'].create({
                'name': f"FAK_Report_{self.year}.pdf",
                'datas': report_pdf,
                'res_id': self.id,
                'res_model': self._name,
            })
            self.message_post(attachment_ids=[attachment.id])

    def generate_ktg_report(self):
        self.ensure_one()
        declaration = self._get_declaration()
        report = self.company_id._l10n_ch_swissdec_request(
            route='generate_report',
            data=declaration,
            is_test=self.test_transmission,
            report_type="KtgReport"
        )
        report_pdf = report.get("KtgReport")
        if report_pdf:
            attachment = self.env['ir.attachment'].create({
                'name': f"KTG_Report_{self.year}.pdf",
                'datas': report_pdf,
                'res_id': self.id,
                'res_model': self._name,
            })
            self.message_post(attachment_ids=[attachment.id])

    def generate_laa_report(self):
        self.ensure_one()
        declaration = self._get_declaration()
        report = self.company_id._l10n_ch_swissdec_request(
            route='generate_report',
            data=declaration,
            is_test=self.test_transmission,
            report_type="UvgReport"
        )
        report_pdf = report.get("UvgReport")
        if report_pdf:
            attachment = self.env['ir.attachment'].create({
                'name': f"LAA_Report_{self.year}.pdf",
                'datas': report_pdf,
                'res_id': self.id,
                'res_model': self._name,
            })
            self.message_post(attachment_ids=[attachment.id])

    def generate_laac_report(self):
        self.ensure_one()
        declaration = self._get_declaration()
        report = self.company_id._l10n_ch_swissdec_request(
            route='generate_report',
            data=declaration,
            is_test=self.test_transmission,
            report_type="UvgzReport"
        )
        report_pdf = report.get("UvgzReport")
        if report_pdf:
            attachment = self.env['ir.attachment'].create({
                'name': f"LAAC_Report_{self.year}.pdf",
                'datas': report_pdf,
                'res_id': self.id,
                'res_model': self._name,
            })
            self.message_post(attachment_ids=[attachment.id])

    def generate_txb_report(self):
        self.ensure_one()
        declaration = self._get_declaration()
        report = self.company_id._l10n_ch_swissdec_request(
            route='generate_report',
            data=declaration,
            is_test=self.test_transmission,
            report_type="TxbReport"
        )
        report_pdf = report.get("TxbReport")
        if report_pdf:
            attachment = self.env['ir.attachment'].create({
                'name': f"TXB_Report_{self.year}.pdf",
                'datas': report_pdf,
                'res_id': self.id,
                'res_model': self._name,
            })
            self.message_post(attachment_ids=[attachment.id])

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
                    'pdf_filename': _("Wage_statement_%(year)s_%(name)s_%(timestamp)s", year=self.year, name=employee.name, timestamp=time.time_ns()),
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
                self.message_post(body=_("Employee with number %s was either archived or deleted. Wage statement will not be sent automatically.", registration), attachment_ids=[attachment.id])

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

    def create_eiv_file(self):
        declare_salary = self._get_declaration()
        result = self.company_id._l10n_ch_swissdec_request(route="create_eiv_file", data=declare_salary, is_test=self.test_transmission)
        message = result['eiv_file']
        if message:
            attachment = self.env['ir.attachment'].create({
                'name': _("EIV_%s.xml", self.name),
                'datas': base64.encodebytes(message.encode()),
                'res_id': self.id,
                'res_model': self._name,
            })
            self.message_post(attachment_ids=[attachment.id], body=_('EIV File Successfully Generated'))

    def _get_posted_mail_template(self):
        return self.env.ref('documents_hr_payroll.mail_template_new_declaration', raise_if_not_found=False)

    def _get_posted_document_owner(self, employee):
        return employee.user_id
