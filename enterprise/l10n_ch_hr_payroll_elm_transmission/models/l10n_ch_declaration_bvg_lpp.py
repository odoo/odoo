# Part of Odoo. See LICENSE file for full copyright and licensing details.
from ..api.swissdec_declarations import SwissdecDeclaration, SwissdecInstitution
from odoo import api, Command, fields, models, _
from odoo.tools.misc import format_date
import datetime
from dateutil.relativedelta import relativedelta

class L10nCHLPPReport(models.Model):
    _name = "l10n.ch.lpp.basis.report"
    _inherit = 'l10n.ch.swissdec.transmitter'
    _description = "BVG-LPP Basis Yearly Declaration"

    lpp_basis_line_ids = fields.One2many("l10n.ch.lpp.basis.report.line", "report_id", readonly=False)

    def action_prepare_data(self):
        self.ensure_one()
        super().action_prepare_data()
        first_day_of_month = datetime.date(self.year, int(self.month), 1)
        last_day_of_month = first_day_of_month + relativedelta(months=1, days=-1)

        all_contracts = self.env['hr.contract'].search([('l10n_ch_lpp_insurance_id', '!=', False),
                                                        ('l10n_ch_lpp_not_insured', '!=', True),
                                                        ('l10n_ch_lpp_insurance_id', '!=', False),
                                                        ('company_id', '=', self.company_id.id)]).filtered(lambda c: (c.date_start <= last_day_of_month and (c.date_end >= first_day_of_month if c.date_end else True)))
        yearly_values = dict(self.env["l10n.ch.employee.yearly.values"]._get_mapped_snapshots(
            domain=[('employee_id', 'in', all_contracts.employee_id.ids)]))

        line_vals = [Command.delete(line.id) for line in self.lpp_basis_line_ids]
        for contract in all_contracts:
            lpp_basis = yearly_values[contract.employee_id][self.year][int(self.month)].bvg_lpp_annual_basis
            line_vals.append(Command.create({
                "report_id": self.id,
                "employee_id": contract.employee_id.id,
                "lpp_institution": contract.l10n_ch_lpp_insurance_id.id,
                "lpp_calculated_basis": lpp_basis,
                "lpp_declared_basis": lpp_basis,
            }))

        self.update({
            "lpp_basis_line_ids": line_vals
        })
        self._compute_l10n_ch_declare_salary_data()


    @api.depends("year", "month", "lpp_basis_line_ids")
    def _compute_l10n_ch_declare_salary_data(self):
        swissdec_declaration = SwissdecDeclaration()
        for declaration in self:
            monthly_values = dict(self.env["l10n.ch.employee.yearly.values"]._get_mapped_snapshots(domain=[('employee_id', 'in', declaration.lpp_basis_line_ids.employee_id.ids)]))
            staff = []

            for lpp_salary in declaration.lpp_basis_line_ids:
                if lpp_salary.employee_id:
                    monthly_snapshot = monthly_values[lpp_salary.employee_id][declaration.year][int(declaration.month)]
                    if monthly_snapshot.person:
                        lpp_salary_declared = swissdec_declaration.create_bvg_lpp_ema(
                            institution_id=lpp_salary.lpp_institution,
                            declarations={},
                            codes=lpp_salary.employee_id.contract_id.l10n_ch_lpp_solutions.mapped('code'),
                            bvg_lpp_annual_basis=lpp_salary.lpp_declared_basis
                        )
                        staff.append({
                            **monthly_snapshot.person,
                            "BVG-LPP-Salaries": {
                                "BVG-LPP-Salary": [lpp_salary_declared]
                            }
                        })

            if staff:
                staff_declaration = {
                    "Staff": {
                        "Person": staff
                    }
                }
                institutions_to_process = list(set(declaration.lpp_basis_line_ids.mapped('lpp_institution')))
                declaration.l10n_ch_declare_salary_data = {
                    **swissdec_declaration.get_company_description(declaration.company_id),
                    **staff_declaration,
                    **swissdec_declaration.get_institutions(institutions_to_process, general_validasof=format_date(self.env, datetime.date( declaration.year, int(declaration.month), 1), date_format='yyyy-MM-dd')),
                    "SalaryCounters": swissdec_declaration.get_salary_tag_counter(staff_declaration),
                    "SalaryTotals": ["XSDSKIP"],
                }

    def _get_institutions(self):
        return list(self.lpp_basis_line_ids.mapped("lpp_institution"))

    def _get_declaration(self):
        self._compute_l10n_ch_declare_salary_data()
        self.ensure_one()
        swissdec_declaration = SwissdecDeclaration()
        return swissdec_declaration.create_declare_salary(
            institutions_to_process=self._get_institutions(),
            company_id=self.company_id,
            staff=self.l10n_ch_declare_salary_data,
            declaration_year=self.year,
            test_case=self.test_transmission,
            substitution_declaration_id=self.substituted_declaration_id.swissdec_declaration_id,
            general_validasof=format_date(self.env, datetime.date(self.year, int(self.month), 1), date_format='yyyy-MM-dd')
        )


class L10nCHLPPBasisReportLine(models.Model):
    _name = "l10n.ch.lpp.basis.report.line"
    _description = "LPP Basis Line"

    employee_id = fields.Many2one("hr.employee", required=True)
    lpp_institution = fields.Many2one("l10n.ch.lpp.insurance", required=True)
    report_id = fields.Many2one("l10n.ch.lpp.basis.report", required=True)
    lpp_calculated_basis = fields.Float()
    lpp_declared_basis = fields.Float()
