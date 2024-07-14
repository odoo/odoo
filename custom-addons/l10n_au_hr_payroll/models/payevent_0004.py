# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
from lxml import etree
from datetime import date
from collections import defaultdict

from odoo import api, fields, models, _
from odoo.tools.misc import file_path


class L10nAuPayEvent0004(models.Model):
    _name = "l10n_au.payevnt.0004"
    _description = "Pay Event 0004"

    name = fields.Char(string="Name", compute="_compute_name")
    payslip_batch_id = fields.Many2one("hr.payslip.run", string="Payslip Batch")
    payslip_ids = fields.Many2many("hr.payslip", string="Payslip")
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        related="payslip_batch_id.currency_id",
        readonly=True)
    payevent_type = fields.Selection(
        selection=[
            ("submit", "Submit"),
            ("update", "Update")],
        string="Type",
        default="submit",
        required=True)
    previous_id_bms = fields.Char(string="Previous BMS ID")
    ffr = fields.Boolean(
        string="Full File Replacement",
        help="Indicates if this report should replace the previous report with the same transaction identifier")
    previous_report_id = fields.Many2one(
        "l10n_au.payevnt.0004", string="Previous Report",
        help="Report which you are updating")
    intermediary = fields.Many2one("res.partner", string="Intermediary")
    submit_date = fields.Date(
        string="Submit Date",
        help="Enter manual submit date if you want to submit the report at a particular date")
    submission_id = fields.Char(
        string="Submission ID",
        readonly=True,
        help="Submission ID of the report")
    # XML report fields
    state = fields.Selection([("generate", "generate"), ("get", "get"), ("sent", "sent")], default="generate")
    xml_file = fields.Binary("XML File", readonly=True, attachment=False)
    xml_filename = fields.Char()
    xml_validation_state = fields.Selection([
        ("normal", "N/A"),
        ("done", "Valid"),
        ("invalid", "Invalid"),
    ], default="normal", compute="_compute_validation_state", store=True)
    error_message = fields.Char("Error Message", compute="_compute_validation_state", store=True)
    warning_message = fields.Char(compute="_compute_warning_message")

    # constraints ffr, cannot be true if type is update
    _sql_constraints = [
        ("ffr", "CHECK(ffr = false OR payevent_type = 'submit')", "Full File Replacement cannot be true if type is 'update'."),
        ("l10n_au_l10n_au_previous_report", "CHECK(previous_report_id != id)", "A report can't update iself.")
    ]

    @api.depends("l10n_au_payevnt_emp_ids")
    def _compute_payee_record_count(self):
        for report in self:
            report.l10n_au_payee_record_count = len(report.l10n_au_payevnt_emp_ids)

    @api.depends("xml_file")
    def _compute_validation_state(self):
        payevent_xsd_root = etree.parse(file_path("l10n_au_hr_payroll/data/l10n_au_payevnt_0004.xsd"))
        payeventemp_xsd_root = etree.parse(file_path("l10n_au_hr_payroll/data/l10n_au_payevntemp_0004.xsd"))
        payevent_schema = etree.XMLSchema(payevent_xsd_root)
        payeventemp_schema = etree.XMLSchema(payeventemp_xsd_root)

        no_xml_file_records = self.filtered(lambda record: not record.xml_file)
        no_xml_file_records.update({
            "xml_validation_state": "normal",
            "error_message": False})
        for record in self - no_xml_file_records:
            xml_root = etree.fromstring(base64.b64decode(record.xml_file))
            payevent_root = xml_root.find("{http://www.sbr.gov.au/ato/payevnt}PAYEVNT")
            payeventemp_roots = xml_root.findall("{http://www.sbr.gov.au/ato/payevntemp}PAYEVNTEMP")
            try:
                payevent_schema.assertValid(payevent_root)
                for payeventemp_root in payeventemp_roots:
                    payeventemp_schema.assertValid(payeventemp_root)
                record.xml_validation_state = "done"
            except etree.DocumentInvalid as err:
                record.xml_validation_state = "invalid"
                record.error_message = str(err)

    @api.depends("payslip_batch_id", "payslip_ids", "payevent_type")
    def _compute_name(self):
        for report in self:
            if report.payslip_batch_id:
                report.name = report.payslip_batch_id.name
            elif report.payslip_ids:
                if len(report.payslip_ids) > 1:
                    report.name = ", ".join(payslip.employee_id.name for payslip in report.payslip_ids[:3])
                    if len(report.payslip_ids) > 3:
                        report.name += ",..."
                report.name = report.payslip_ids[0].employee_id.name
            else:
                report.name = ""

    def _compute_warning_message(self):
        for report in self:
            company_warnings, user_warnings = [], []
            if not self.env.company.zip:
                company_warnings.append("Postcode.")
            if not self.env.company.country_id:
                company_warnings.append("Country.")
            if not self.env.user.work_email:
                user_warnings.append("Work Email.")
            if not self.env.user.work_phone:
                user_warnings.append("Work Phone.")
            message = ""
            if company_warnings:
                message += "\n  ・ ".join(["Missing required company information:"] + company_warnings)
            if user_warnings:
                message += "\n  ・ ".join(["Missing required user information:"] + user_warnings)
            report.warning_message = message

    def _get_complex_rendering_data(self, payslips_ids):
        today = fields.Date.today()
        financial_year = today.year if today.month > 6 else today.year - 1
        start_financial_year = date(financial_year, 7, 1)
        employees = payslips_ids.employee_id

        # == Date and Run Date ==
        if self.payevent_type == "submit":
            run_date = self.payslip_batch_id.paid_date or self.create_date
            submit_date = self.payslip_batch_id.paid_date or self.create_date
        elif self.payevent_type == "update":
            run_date = self.payslip_batch_id.paid_date or self.create_date
            submit_date = self.submit_date or self.create_date
            if self.submit_date < start_financial_year:
                submit_date = start_financial_year

        # == Totals == (may not be reported in an update event)
        line_codes = ["GROSS", "WITHHOLD.TOTAL"]
        all_line_values = payslips_ids._get_line_values(line_codes, vals_list=['total', 'quantity'])
        mapped_total = {
            code: sum(all_line_values[code][p.id]['total'] for p in payslips_ids) for code in line_codes
        }
        paygw = -mapped_total["WITHHOLD.TOTAL"]
        gross = mapped_total["GROSS"]
        child_garnish = 0.0
        child_withhold = 0.0

        extra_data = {
            "PaymentRecordTransactionD": submit_date.date(),
            "MessageTimestampGenerationDt": run_date.isoformat(),
            "PayAsYouGoWithholdingTaxWithheldA": paygw,
            "TotalGrossPaymentsWithholdingA": gross,
            "ChildSupportGarnisheeA": child_garnish,
            "ChildSupportWithholdingA": child_withhold,
        }
        # Employees extra data
        unknown_date = date(1800, 1, 1)
        min_date = date(1950, 1, 1)
        for employee in employees:
            payslips = payslips_ids.filtered(lambda p: p.employee_id == employee)
            start_date = max(min_date, employee.first_contract_date) or unknown_date
            remunerations = []
            deductions = []
            for payslip in payslips:
                Remuneration = defaultdict(lambda: False)
                worked_lines_ids = payslip.worked_days_line_ids
                input_lines_ids = payslip.input_line_ids
                contract_id = payslip.contract_id
                # == Gross, income type, paygw ==
                Remuneration["IncomeStreamTypeC"] = payslip.l10n_au_income_stream_type
                # == Foreign income == (required for FEI, IAA, WHM )
                if payslip.l10n_au_income_stream_type in ["FEI", "IAA", "WHM"]:
                    Remuneration["AddressDetailsCountryC"] = employee.private_country_id.code.lower()
                    Remuneration["IncomeTaxForeignWithholdingA"] = payslip.l10n_au_foreign_tax_withheld
                    Remuneration["IndividualNonBusinessExemptForeignEmploymentIncomeA"] = payslip.l10n_au_exempt_foreign_income
                Remuneration["IncomeTaxPayAsYouGoWithholdingTaxWithheldA"] = -all_line_values["WITHHOLD.TOTAL"][payslip.id]["total"]
                Remuneration["GrossA"] = all_line_values["GROSS"][payslip.id]["total"]
                # == Paid Leave ==
                leave_lines = worked_lines_ids.filtered(lambda l: l.work_entry_type_id.is_leave)
                Remuneration["PaidLeaveCollection"] = []
                for leave in leave_lines:
                    Remuneration["PaidLeaveCollection"].append({
                        "TypeC": leave.work_entry_type_id.code,
                        "PaymentA": leave.amount,
                    })
                # == Allowance ==
                allowance_lines = input_lines_ids.sudo().filtered(lambda l: l.input_type_id.l10n_au_is_allowance)
                Remuneration["AllowanceCollection"] = []
                for allowance in allowance_lines:
                    Remuneration["AllowanceCollection"].append({
                        "TypeC": allowance.code,
                        "OtherAllowanceTypeDe": allowance.name if allowance.code == "OD" else "",
                        "PaymentA": allowance.amount,
                    })
                # == Overtime ==
                overtime_work_entry_type = self.env.ref("hr_work_entry.overtime_work_entry_type")
                overtime_lines = worked_lines_ids.filtered(lambda l: l.work_entry_type_id == overtime_work_entry_type)
                Remuneration["OvertimePaymentA"] = sum(overtime_lines.mapped("amount"))
                # == Bonuses and commissions ==
                bonus_commission_input_type = self.env.ref("l10n_au_hr_payroll.input_gross_bonuses_and_commissions")
                bonus_commissions_lines = input_lines_ids.filtered(lambda l: l.input_type_id == bonus_commission_input_type)
                Remuneration["GrossBonusesAndCommissionsA"] = sum(bonus_commissions_lines.mapped("amount"))
                # == Directors fees ==
                directors_fee_input_type = self.env.ref("l10n_au_hr_payroll.input_gross_director_fee")
                directors_fee_lines = input_lines_ids.filtered(lambda l: l.input_type_id == directors_fee_input_type)
                Remuneration["GrossDirectorsFeesA"] = sum(directors_fee_lines.mapped("amount"))
                # == CDEP ==
                cdep_input_type = self.env.ref("l10n_au_hr_payroll.input_gross_cdep")
                cdep_lines = input_lines_ids.filtered(lambda l: l.input_type_id == cdep_input_type)
                Remuneration["IndividualNonBusinessCommunityDevelopmentEmploymentProjectA"] = sum(cdep_lines.mapped("amount"))
                # == Salary sacrifice ==
                Remuneration["SalarySacrificeCollection"] = [
                    {"TypeC": "S", "PaymentA": contract_id.l10n_au_salary_sacrifice_superannuation},
                    {"TypeC": "O", "PaymentA": contract_id.l10n_au_salary_sacrifice_other},
                ]
                # == Lump Sum (Loempia sum) ==
                Remuneration["LumpSumCollection"] = []
                remunerations.append(Remuneration)

                # == DEDUCTIONS ==
                if contract_id.l10n_au_workplace_giving:
                    deductions.append({
                        "RemunerationTypeC": "W",
                        "RemunerationA": contract_id.l10n_au_workplace_giving,
                    })
                if contract_id.employee_id.l10n_au_child_support_garnishee_amount:
                    deductions.append({
                        "RemunerationTypeC": "G",
                        "RemunerationA": contract_id.employee_id.l10n_au_child_support_garnishee_amount,
                    })
                if contract_id.employee_id.l10n_au_child_support_deduction:
                    deductions.append({
                        "RemunerationTypeC": "D",
                        "RemunerationA": contract_id.employee_id.l10n_au_child_support_deduction,
                    })

            employee_data = {
                "EmploymentStartD": start_date,
                "Remuneration": remunerations,
                "Deduction": deductions,
            }

            extra_data.update({
                employee.id: employee_data
            })

        return extra_data

    def _get_rendering_data(self, payslips_ids):
        extra_data = self._get_complex_rendering_data(payslips_ids)
        employer = defaultdict(str, {
            "SoftwareInformationBusinessManagementSystemId": "125b8925-9a97-4178-8dee-78d3fdeb0437",  # placeholder
            "AustralianBusinessNumberId": self.env.company.vat or False,
            "WithholdingPayerNumberId": self.env.company.l10n_au_wpn_number if not self.env.company.vat else "",
            "OrganisationDetailsOrganisationBranchC": self.env.company.l10n_au_branch_code,
            "PreviousSoftwareInformationBusinessManagementSystemId": self.previous_id_bms,   # placeholder
            "DetailsOrganisationalNameT": self.env.company.name,
            "PersonUnstructuredNameFullNameT": self.env.user.name,
            "ElectronicMailAddressT": self.env.user.work_email,
            "TelephoneMinimalN": self.env.user.work_phone,
            "PostcodeT": self.env.company.zip,
            "CountryC": self.env.company.country_id.code.lower(),
            "PaymentRecordTransactionD": extra_data["PaymentRecordTransactionD"],
            "InteractionRecordCt": len(payslips_ids),
            "MessageTimestampGenerationDt": extra_data["MessageTimestampGenerationDt"],
            "InteractionTransactionId": "",  # filled later
            "AmendmentI": "true" if self.ffr else "false",
            "SignatoryIdentifierT": self.env.user.name,
            "SignatureD": date.today(),
            "StatementAcceptedI": "true",
        })
        if self.payevent_type == "submit":
            employer.update({
                "PayAsYouGoWithholdingTaxWithheldA": extra_data["PayAsYouGoWithholdingTaxWithheldA"],
                "TotalGrossPaymentsWithholdingA": extra_data["TotalGrossPaymentsWithholdingA"],
                "ChildSupportGarnisheeA": extra_data["ChildSupportGarnisheeA"],
                "ChildSupportWithholdingA": extra_data["ChildSupportWithholdingA"],
            })

        intermediary = defaultdict(str)
        intermediary_id = self.intermediary
        if intermediary_id:
            intermediary.update({
                "AustralianBusinessNumberId": intermediary_id.vat,
                "TaxAgentNumberId": intermediary_id.l10n_au_ran_number,
                "PersonUnstructuredNameFullNameT": intermediary_id.name,
                "ElectronicMailAddressT": intermediary_id.email,
                "TelephoneMinimalN": intermediary_id.phone,
                "SignatoryIdentifierT": intermediary_id.name,
                "SignatureD": False,
                "StatementAcceptedI": False,
            })
        employees = []
        for payslip in payslips_ids:
            employee = payslip.employee_id

            values = defaultdict(str, {
                "TaxFileNumberId": employee.l10n_au_tfn,
                "AustralianBusinessNumberId": employee.l10n_au_abn,
                "EmploymentPayrollNumberId": employee.registration_number or str(employee.id),
                "PreviousPayrollIDEmploymentPayrollNumberId": employee.l10n_au_previous_id_bms,
                "FamilyNameT": ' '.join(employee.name.split(' ')[1:]),
                "GivenNameT": employee.name.split(' ')[0],
                "OtherGivenNameT": "",
                "Dm": employee.birthday.day,
                "M": employee.birthday.month,
                "Y": employee.birthday.year,
                "Line1T": employee.private_street,
                "Line2T": employee.private_street2,
                "LocalityNameT": employee.private_city,
                "StateOrTerritoryC": employee.private_state_id.code,
                "PostcodeT": employee.private_zip,
                "CountryC": employee.private_country_id.code.lower() if employee.private_country_id else False,
                "ElectronicMailAddressT": employee.work_email,
                "TelephoneMinimalN": employee.work_phone,
                "EmploymentStartD": extra_data[employee.id]["EmploymentStartD"],
                "EmploymentEndD": False,
                "PaymentBasisC": payslip.contract_id.l10n_au_employment_basis_code,
                "CessationTypeC": payslip.contract_id.l10n_au_cessation_type_code,
                "TaxTreatmentC": payslip.contract_id.l10n_au_tax_treatment_code,
                "TaxOffsetClaimTotalA": employee.l10n_au_nat_3093_amount,
                "StartD": payslip.date_from,
                "EndD": payslip.date_to,
                "RemunerationPayrollEventFinalI": str(payslip.struct_id.code == "AUTERM").lower(),
                # Remuneration collection
                "Remuneration": extra_data[employee.id]["Remuneration"],
                # Deductions
                "Deduction": extra_data[employee.id]["Deduction"],
                # Super Contributions
                "EntitlementTypeC": False,
                "EmployerContributionsYearToDateA": False,
                # Fringe Benefits
                "FringeBenefitsReportableExemptionC": False,
                "A": False,
            })
            employees.append(values)

        # sequence at the end to avoid generating if there was an error
        self.submission_id = self.env['ir.sequence'].next_by_code("payevent0004.transaction")
        employer["InteractionTransactionId"] = self.submission_id
        return {"employer": employer, "employees": employees, "intermediary": intermediary}

    def action_generate_xml(self):
        self.ensure_one()
        self.xml_filename = '%s-PAYEVNT.0004.xml' % (self.name)
        report = self.env['ir.qweb']._render('l10n_au_hr_payroll.payevent_0004_xml_report', self._get_rendering_data(self.payslip_ids))

        # Prettify xml string
        root = etree.fromstring(report, parser=etree.XMLParser(remove_blank_text=True, resolve_entities=False))
        xml_str = etree.tostring(root, pretty_print=True, encoding='utf-8', xml_declaration=True)

        self.xml_file = base64.b64encode(xml_str)
        self.state = 'get'


class L10nAuPayevntEmp(models.Model):
    _name = "l10n_au.payevnt.emp.0004"
    _description = "Pay Event Employee"

    employee_id = fields.Many2one(
        "hr.employee", string="Employee", required=True)
    payslip_id = fields.Many2one(
        "hr.payslip", string="Payslip", required=True)
    payslip_currency_id = fields.Many2one(
        "res.currency", related="payslip_id.currency_id", readonly=True)
    payevnt_0004_id = fields.Many2one(
        "l10n_au.payevnt.0004", string="Pay Event 0004")
