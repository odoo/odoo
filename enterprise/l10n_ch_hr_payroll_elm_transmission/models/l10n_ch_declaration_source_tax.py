# Part of Odoo. See LICENSE file for full copyright and licensing details.

from ..api.swissdec_declarations import SwissdecDeclaration, SwissdecInstitution
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class L10nCHInsuranceReport(models.Model):
    _name = "l10n.ch.is.report"
    _inherit = ['l10n.ch.is.report', 'l10n.ch.swissdec.transmitter']

    source_tax_institution_ids = fields.Many2many("l10n.ch.source.tax.institution")

    def action_prepare_data(self):
        self.ensure_one()
        super().action_prepare_data()
        declaration, institutions = self.env["l10n.ch.employee.yearly.values"]._get_monthly_tax_at_source(year=self.year, month=int(self.month), company_id=self.company_id)
        self.source_tax_institution_ids = self.env['l10n.ch.source.tax.institution'].browse(institutions.get("QST", []))

        previous_st_decl = self.env['l10n.ch.swissdec.declaration'].search(
            [('month', '=', self.month),
             ('year', '=', self.year),
             ('res_model', '=', self._name),
             ('test_transmission', '=', False),
             ('l10n_ch_swissdec_job_result_ids', '!=', False)],
            order="transmission_date desc",
            limit=1
        )
        if previous_st_decl:
            corresponding_report = self.env['l10n.ch.is.report'].search([('id', '=', previous_st_decl.res_id)])
            if corresponding_report and set(corresponding_report.source_tax_institution_ids.ids).intersection(set(self.source_tax_institution_ids.ids)) and not (self.replacement_declaration or self.substituted_declaration_id):
                raise ValidationError(_("You cannot replace a Source-Tax Declaration, please indicate the declaration to be substituted.\n A replacement declaration can only be sent after consultation with all the concerned Tax Authorities."))

        last_declaration = self.env['l10n.ch.swissdec.declaration'].search(
            [('res_model', '=', self._name),
             ('test_transmission', '=', False),
             ('l10n_ch_swissdec_job_result_ids', '!=', False)],
            order="transmission_date desc",
            limit=1
        )

        if previous_st_decl and self.replacement_declaration and self.substituted_declaration_id:
            if self.substituted_declaration_id.id != last_declaration.id:
                raise ValidationError(_("Only the last Source-Tax Declaration can be substituted."))

        self.l10n_ch_declare_salary_data = declaration

    def _get_institutions(self):
        institutions = list(self.source_tax_institution_ids)
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

    def generate_st_report(self):
        self.ensure_one()
        declaration = self._get_declaration()

        institutions = declaration.get('SalaryDeclaration', {}).get('Company', {}).get("Institutions", {}).get('TaxAtSource', [])
        for institution in institutions:

            report = self.company_id._l10n_ch_swissdec_request(
                route='generate_source_tax_report',
                data=declaration,
                is_test=self.test_transmission,
                canton_id=institution.get('institutionID')
            )
            report_pdf = report.get("QST_Report")
            if report_pdf:
                self.env['ir.attachment'].create({
                    'name': f"QST_Report_{institution.get('CantonID')}_{self.year}_{self.month.zfill(2)}.pdf",
                    'datas': report_pdf,
                    'res_id': self.id,
                    'res_model': self._name,
                })
