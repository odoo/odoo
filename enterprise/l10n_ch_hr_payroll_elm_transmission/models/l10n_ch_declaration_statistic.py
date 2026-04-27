# Part of Odoo. See LICENSE file for full copyright and licensing details.

from ..api.swissdec_declarations import SwissdecDeclaration, SwissdecInstitution
from odoo import api, fields, models, _


class L10nCHInsuranceReport(models.Model):
    _name = "l10n.ch.statistic.report"
    _inherit = ['l10n.ch.swissdec.transmitter']
    _description = "Monthly Statistic Report"

    def action_prepare_data(self):
        self.ensure_one()
        super().action_prepare_data()
        declaration, institutions = self.env["l10n.ch.employee.yearly.values"]._get_monthly_statistic(year=self.year, month=int(self.month), company_id=self.company_id)
        self.l10n_ch_declare_salary_data = declaration


    def _get_institutions(self):
        return [SwissdecInstitution("BFS", pay_agreement=self.company_id.l10n_ch_statistics_convention, payroll_unit=self.company_id.l10n_ch_statistics_payroll_unit)]

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

    def generate_statistic_report(self):
        self.ensure_one()
        declaration = self._get_declaration()
        report = self.company_id._l10n_ch_swissdec_request(
            route='generate_report',
            data=declaration,
            is_test=self.test_transmission,
            report_type="StatisticReport"
        )
        report_pdf = report.get("StatisticReport")
        if report_pdf:
            attachment = self.env['ir.attachment'].create({
                'name': f"Statistic_Report_{self.year}_{self.month.zfill(2)}.pdf",
                'datas': report_pdf,
                'res_id': self.id,
                'res_model': self._name,
            })
            self.message_post(attachment_ids=[attachment.id])
