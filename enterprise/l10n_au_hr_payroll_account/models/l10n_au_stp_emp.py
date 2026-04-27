from odoo import api, Command, fields, models, _
from odoo.exceptions import ValidationError


class L10nAuSTPEmp(models.Model):
    _name = "l10n_au.stp.emp"
    _description = "STP Employee"

    employee_id = fields.Many2one(
        "hr.employee", string="Employee", required=True)
    payslip_ids = fields.Many2many(
        "hr.payslip", string="Payslip", compute="_compute_ytd")
    ytd_balance_ids = fields.Many2many(
        "l10n_au.payslip.ytd", string="YTD Balances", compute="_compute_ytd")
    currency_id = fields.Many2one(
        "res.currency", related="stp_id.currency_id", readonly=True)
    stp_id = fields.Many2one(
        "l10n_au.stp", string="Single Touch Payroll")
    ytd_gross = fields.Monetary("Total Gross", compute="_compute_ytd")
    ytd_tax = fields.Monetary("Total Tax", compute="_compute_ytd")
    ytd_super = fields.Monetary("Total Super", compute="_compute_ytd")
    ytd_rfba = fields.Monetary("Total RFBA", compute="_compute_ytd")
    ytd_rfbae = fields.Monetary("Total RFBA-E", compute="_compute_ytd")

    @api.depends("employee_id", "stp_id.start_date", "stp_id.end_date")
    def _compute_ytd(self):
        for emp in self:

            if not emp.employee_id:
                emp.update(
                    {
                        "payslip_ids": False,
                        "ytd_balance_ids": False,
                        "ytd_gross": False,
                        "ytd_tax": False,
                        "ytd_super": False,
                        "ytd_rfba": False,
                        "ytd_rfbae": False,
                    }
                )
                continue
            # Reverse the finalisation flag if the STP is not draft
            finalisation = False
            if emp.stp_id.is_finalisation:
                finalisation = emp.stp_id.state != "draft"
            elif emp.stp_id.is_unfinalisation:
                finalisation = emp.stp_id.state == "draft"

            payslip_ids, ytd_balance_ids = emp.employee_id._get_fiscal_year_data(
                emp.stp_id.start_date, emp.stp_id.end_date, finalised=finalisation)
            emp.update({
                "payslip_ids": [Command.set(payslip_ids)],
                "ytd_balance_ids": [Command.set(ytd_balance_ids)],
            })
            # Check if the employee has already been finalised or unfinalised
            if not emp.payslip_ids and not emp.ytd_balance_ids:
                if emp.stp_id.is_finalisation:
                    raise ValidationError(_("There is no data to finalise for employee %s for the selected Fiscal year. "
                                            "Please unfinalise the employee to make any adjustments.", emp.employee_id.name))
                elif emp.stp_id.is_unfinalisation:
                    raise ValidationError(_("There is no data to unfinalise for employee %s for the selected Fiscal year.", emp.employee_id.name))
                else:
                    raise ValidationError(_("This employee has no payslips for the Current."))

            last_payslip = emp.payslip_ids.sorted("date_from", reverse=True)[:1]
            fields_to_compute = [
                "l10n_au_foreign_tax_withheld",
                "l10n_au_exempt_foreign_income",
                "l10n_au_salary_sacrifice_other",
                "l10n_au_salary_sacrifice_superannuation",
                "l10n_au_extra_negotiated_super",
                "l10n_au_extra_compulsory_super",
            ]
            ytd_vals = last_payslip._l10n_au_get_year_to_date_totals(fields_to_compute=fields_to_compute, l10n_au_include_current_slip=True, employee_id=emp.employee_id.id, start_date=emp.stp_id.start_date)
            input_vals = last_payslip._l10n_au_get_ytd_inputs(l10n_au_include_current_slip=True, employee_id=emp.employee_id.id, start_date=emp.stp_id.start_date)
            ytd_gross = filter(lambda item: item[1]['payroll_code'] == "G", ytd_vals['worked_days'].items())
            emp.ytd_gross = sum(line[1]['amount'] for line in ytd_gross)

            emp.ytd_tax = abs(ytd_vals['slip_lines']['WITHHOLD.TOTAL']['WITHHOLD.TOTAL'])

            super_liability = ytd_vals["slip_lines"]["SUPER"]["SUPER"] + ytd_vals["fields"]["l10n_au_extra_compulsory_super"]
            super_contribution = ytd_vals["slip_lines"]["SALARY.SACRIFICE"]["SUPER.CONTRIBUTION"] - ytd_vals["fields"]["l10n_au_extra_compulsory_super"]
            emp.ytd_super = super_contribution + super_liability
            emp.ytd_rfba = sum(item[1]['amount'] for item in filter(lambda item: item[1]["code"] == 'FBT' and item[1]["payroll_code"] == "T", input_vals.items()))
            emp.ytd_rfbae = sum(item[1]['amount'] for item in filter(lambda item: item[1]["code"] == 'FBT' and item[1]["payroll_code"] == "E", input_vals.items()))
