# Part of Odoo. See LICENSE file for full copyright and licensing details.
import datetime
from collections import defaultdict

from odoo import _, api, fields, models, Command
from odoo.tools.misc import format_date, file_path
from odoo.tools.float_utils import float_round

from ..api.swissdec_declarations import SwissdecDeclaration
from dateutil.relativedelta import relativedelta

ALLOWED_EDUCATION = ['universityBachelor', 'universityMaster', 'higherEducationMaster', 'higherEducationBachelor', 'higherVocEducation', 'higherVocEducationMaster', 'higherVocEducationBachelor', 'teacherCertificate', 'universityEntranceCertificate', 'vocEducationCompl', 'enterpriseEducation', 'mandatorySchoolOnly', 'doctorate']
STATISTICS_RULE_MAPPING = {
    "Monthly": {
        "I": "GrossBaseSalaryAndRegularAllowance",
        "J": "Allowances",
        "K": "FamilyIncomeSupplement",
        "Y": "PaymentsByThird",
        "L": "SocialContributions",
        "M": "BVG-LPP-RegularContribution"
    },
    "Annual": {
        "P": "Overtime",
        "O": "Earnings13th",
        "Q": "SporadicBenefits",
        "R": "FringeBenefits",
        "S": "CapitalPayment",
        "T": "OtherBenefits"
    }
}
XSD_SKIP_VALUE = "XSDSKIP"
MISSING_VALUE = "XSDMISSING"
XSD_YMONTH = "XSDGYEARMONTH"

class L10nCHEmployeeMonthlySnapshot(models.Model):
    _name = "l10n.ch.employee.monthly.values"
    _description = "Swiss Employee yearly history"
    _order = "month asc"

    yearly_values_id = fields.Many2one('l10n.ch.employee.yearly.values', ondelete="cascade", required=True)
    employee_id = fields.Many2one(related="yearly_values_id.employee_id")
    year = fields.Integer(related="yearly_values_id.year")
    month = fields.Integer(required=True)

    payroll_month_closed = fields.Boolean()
    employee_meta_data = fields.Json(string="Metadata", compute="_compute_employee_meta_data", store=True)
    person = fields.Json(string="Historical Field Values", compute="_compute_person", store=True)
    bvg_lpp_annual_basis = fields.Float(compute="_compute_bvg_lpp_annual_basis", store=True)
    monthly_statistics = fields.Json(string="Monthly Statistic Salaries", compute="_compute_monthly_statistics", store=True)
    additional_particular = fields.Json(string="Tax-At-Source Additional Particular", compute="_compute_additional_particular", store=True)
    lpp_mutations = fields.One2many("l10n.ch.lpp.mutation", "employee_snapshot_id", compute="_compute_mutations", store=True)
    is_mutations = fields.One2many("l10n.ch.is.mutation", "employee_snapshot_id", compute="_compute_mutations", store=True)

    validation_errors = fields.Json(compute="_compute_validation_errors")

    _sql_constraints = [
        ('ch_month_constraint', 'CHECK(month BETWEEN 1 AND 12)',
         'The month must be between 1 and 12.')
    ]

    @staticmethod
    def _fill_xml_scheme(dict, code, value, condition=False, lambda_f=lambda v: v, res_field=None, res_model=None, res_id=None):
        if value or condition:
            computed = lambda_f(value)
            if computed:
                dict[code] = computed
            else:
                dict[code] = {
                    "_missing_": True,
                    "res_model": res_model,
                    "res_id": res_id,
                    "res_field": res_field,
                }

    @staticmethod
    def _amount2str(amount):
        return "{:.2f}".format(amount)

    def _get_additional_meta_data(self):
        if 'l10n_ch_telework_percentage' not in self.employee_id:
            return {}
        return {
            "TeleWorkPercentage": self._amount2str(self.employee_id.l10n_ch_telework_percentage * 100)
        }

    def _get_additional_txb_values(self):
        values = {}

        telework_percentage = "0.00"
        if self.employee_meta_data and self.employee_meta_data.get('TeleWorkPercentage', False):
            telework_percentage = self.employee_meta_data.get('TeleWorkPercentage')
        values["TeleWorkPercentage"] = telework_percentage

        return values

    def _get_additional_avs_values(self, avs_base, avs_status):
        values = {
            'AHV-AVS-BaseSalary': self._amount2str(avs_base)
        }
        if avs_status == 'retired_wave_deduct':
            values["WaiveOfPensionDeduct"] = XSD_SKIP_VALUE

        return values


    @api.depends('yearly_values_id', 'month')
    def _compute_employee_meta_data(self):
        swissdec_helper = SwissdecDeclaration()
        for snapshot in self:
            meta_data = {
                "st-code": snapshot.employee_id.l10n_ch_tax_code or "",
                "st-canton": snapshot.employee_id.l10n_ch_source_tax_canton or "",
                "st-municipality": snapshot.employee_id.l10n_ch_source_tax_municipality or "",
                "children_deduction": snapshot.employee_id.children,
                "st-type": snapshot.employee_id.l10n_ch_tax_scale_type,
                "aci_approved": "GrantTaxAtSourceCode" if snapshot.employee_id.l10n_ch_tax_specially_approved else "",
                "txb-code": f"{snapshot.employee_id.private_country_id.code}-{snapshot.employee_id.l10n_ch_source_tax_canton}" if snapshot.employee_id.l10n_ch_cross_border_commuter and snapshot.employee_id.l10n_ch_source_tax_canton else "",
                "lpp_institution": swissdec_helper.get_institution_id_ref(snapshot.employee_id.contract_id.l10n_ch_lpp_insurance_id) if snapshot.employee_id.contract_id.l10n_ch_lpp_insurance_id and not snapshot.employee_id.contract_id.l10n_ch_lpp_not_insured else "",
                "lpp_codes": sorted(snapshot.employee_id.contract_id.l10n_ch_lpp_solutions.mapped('code')),
                "Particulars": snapshot.person.get("Particulars", {}) if snapshot.person else {},
                "Work": snapshot.person.get("Work", {}) if snapshot.person else {},
                "Statistic": {},
                "AdditionalParticulars": snapshot.additional_particular if snapshot.additional_particular else {},
                "ContractValues": {},
                "EmployeeValues": {},
                **snapshot._get_additional_meta_data()
            }

            if snapshot.employee_id.contract_id:
                relevant_contract = snapshot.employee_id.contract_id
                self._fill_xml_scheme(meta_data['Statistic'], "Position", relevant_contract.l10n_ch_job_type, True, res_model='hr.contract', res_id=relevant_contract.id, res_field="l10n_ch_job_type")
                self._fill_xml_scheme(meta_data['Statistic'], "Education", snapshot.employee_id.certificate, True, lambda_f=lambda c: c if c in ALLOWED_EDUCATION else False, res_model='hr.employee', res_id=snapshot.employee_id.id, res_field="certificate")
                self._fill_xml_scheme(meta_data['Statistic'], "JobTitle", relevant_contract.job_id.name, True, res_model='hr.contract', res_id=relevant_contract.id, res_field="job_id")
                self._fill_xml_scheme(meta_data['Statistic'], "LeaveEntitlement", relevant_contract.l10n_ch_yearly_holidays, True, lambda_f=lambda l: l or "0")

                self._fill_xml_scheme(meta_data['ContractValues'], "AVS", relevant_contract.l10n_ch_social_insurance_id, True, lambda_f=lambda i: i.id if i else False, res_model='hr.contract', res_id=relevant_contract.id, res_field="l10n_ch_social_insurance_id")
                self._fill_xml_scheme(meta_data['ContractValues'], "CAF", relevant_contract.l10n_ch_compensation_fund_id, condition=not relevant_contract.l10n_ch_lpp_not_insured, lambda_f=lambda i: i.id if i else False, res_model='hr.contract', res_id=relevant_contract.id, res_field="l10n_ch_compensation_fund_id")
                self._fill_xml_scheme(meta_data['ContractValues'], "LPP", relevant_contract.l10n_ch_lpp_insurance_id, condition=not relevant_contract.l10n_ch_lpp_not_insured, lambda_f=lambda i: i.id if i else False, res_model='hr.contract', res_id=relevant_contract.id, res_field="l10n_ch_lpp_insurance_id")
                self._fill_xml_scheme(meta_data['ContractValues'], "LAA", relevant_contract.l10n_ch_laa_group, condition=True, lambda_f=lambda i: i.id if i else False, res_model='hr.contract', res_id=relevant_contract.id, res_field="l10n_ch_laa_group")
                self._fill_xml_scheme(meta_data['ContractValues'], "Workplace", relevant_contract.l10n_ch_location_unit_id, condition=True, lambda_f=lambda i: i.id if i else False, res_model='hr.contract', res_id=relevant_contract.id, res_field="l10n_ch_location_unit_id")
                self._fill_xml_scheme(meta_data['ContractValues'], "ContractType", relevant_contract.contract_type_id, condition=True, lambda_f=lambda i: i.id if i else False, res_model='hr.contract', res_id=relevant_contract.id, res_field="contract_type_id")

            if snapshot.employee_id.l10n_ch_has_withholding_tax:
                self._fill_xml_scheme(meta_data['EmployeeValues'], "SourceTaxCanton", snapshot.employee_id.l10n_ch_source_tax_canton, condition=True, res_model='hr.employee', res_id=snapshot.employee_id.id, res_field="l10n_ch_source_tax_canton")
                self._fill_xml_scheme(meta_data['EmployeeValues'], "SourceTaxMunicipality", snapshot.employee_id.l10n_ch_source_tax_municipality, condition=True, res_model='hr.employee', res_id=snapshot.employee_id.id, res_field="l10n_ch_source_tax_municipality")
                self._fill_xml_scheme(meta_data['EmployeeValues'], "SourceTaxCode", snapshot.employee_id.l10n_ch_tax_code, condition=True, res_model='hr.employee', res_id=snapshot.employee_id.id, res_field="l10n_ch_tax_code")


            residence = dict()
            if snapshot.employee_id.l10n_ch_canton != "EX" and snapshot.employee_id.l10n_ch_canton:
                self._fill_xml_scheme(residence, "CantonCH", snapshot.employee_id.l10n_ch_canton, True)
            else:
                self._fill_xml_scheme(residence, "AbroadCountry", snapshot.employee_id.private_country_id, lambda_f=lambda c: str(c.code) if c else False , condition=True, res_model='hr.employee', res_id=snapshot.employee_id.id, res_field="private_country_id")
                if snapshot.employee_id.l10n_ch_residence_type == "Weekly":
                    residence["KindOfResidence"] = {
                        "Weekly": {
                            "Country": "SWITZERLAND"
                        }
                    }
                    self._fill_xml_scheme(residence["KindOfResidence"]["Weekly"], "Street", snapshot.employee_id.l10n_ch_weekly_residence_address_street, False)
                    self._fill_xml_scheme(residence["KindOfResidence"]["Weekly"], "ZIP-Code", snapshot.employee_id.l10n_ch_weekly_residence_address_zip, True, res_model='hr.employee', res_id=snapshot.employee_id.id, res_field="l10n_ch_weekly_residence_address_zip")
                    self._fill_xml_scheme(residence["KindOfResidence"]["Weekly"], "City", snapshot.employee_id.l10n_ch_weekly_residence_address_city, True, res_model='hr.employee', res_id=snapshot.employee_id.id, res_field="l10n_ch_weekly_residence_address_city")

                    self._fill_xml_scheme(meta_data['EmployeeValues'], "weekly_canton", snapshot.employee_id.l10n_ch_weekly_residence_canton, True, res_model='hr.employee', res_id=snapshot.employee_id.id, res_field="l10n_ch_weekly_residence_canton")
                    self._fill_xml_scheme(meta_data['EmployeeValues'], "weekly_municipality", snapshot.employee_id.l10n_ch_weekly_residence_municipality, True, res_model='hr.employee', res_id=snapshot.employee_id.id, res_field="l10n_ch_weekly_residence_municipality")
                else:
                    residence["KindOfResidence"] = {
                        "Daily": XSD_SKIP_VALUE
                    }
            meta_data["Residence"] = residence
            snapshot.employee_meta_data = meta_data

    @api.depends('yearly_values_id', 'month')
    def _compute_person(self):
        mapped_contracts = dict(self.env["hr.contract"]._read_group(domain=[
            ('state', 'in', ['open', 'close']),
        ], groupby=["employee_id"],
            aggregates=["id:recordset"]
        ))

        for snapshot in self:
            employee = snapshot.employee_id

            particular = dict()
            work = dict()
            civil_status = dict()

            address = {
                "Address": {}
            }

            self._fill_xml_scheme(address["Address"], "ZIP-Code", employee.private_zip, condition=True, res_model='hr.employee', res_id=employee.id, res_field="private_zip")
            self._fill_xml_scheme(address["Address"], "City", employee.private_city, condition=True, res_model='hr.employee', res_id=employee.id, res_field="private_city")
            self._fill_xml_scheme(address["Address"], "Country", employee.with_context(lang='en_US').private_country_id, lambda_f=lambda c: c.name.upper())
            self._fill_xml_scheme(address["Address"], "Street", employee.private_street)

            social_insurance_identification = {
                "Social-InsuranceIdentification": {
                    "SV-AS-Number": employee.l10n_ch_sv_as_number
                } if employee.l10n_ch_sv_as_number else {
                    "unknown": XSD_SKIP_VALUE
                }
            }
            employee_contracts = mapped_contracts.get(snapshot.employee_id, self.env['hr.contract'])
            end_of_month = datetime.date(snapshot.year, snapshot.month, 1) + relativedelta(days=-1, months=1)
            valid_contracts_this_month = employee_contracts.filtered(lambda c: c.date_start <= end_of_month).sorted("date_start")
            if valid_contracts_this_month:
                current_contract = valid_contracts_this_month[-1]
                withdrawals_prior_month_end = [d for d in valid_contracts_this_month.mapped("date_end") if d and d <= end_of_month]
                last_withdrawal = max(withdrawals_prior_month_end) if withdrawals_prior_month_end else False
                if current_contract.irregular_working_time:
                    working_time = {
                        "Unsteady": XSD_SKIP_VALUE
                    }
                else:
                    working_time = {}
                    hours_dict = {}
                    self._fill_xml_scheme(hours_dict, "WeeklyHours", current_contract.l10n_ch_weekly_hours, lambda_f=lambda h: self._amount2str(h))
                    self._fill_xml_scheme(hours_dict, "WeeklyLessons", current_contract.l10n_ch_weekly_lessons,  lambda_f=lambda h: self._amount2str(h))
                    if current_contract.l10n_ch_weekly_hours and current_contract.l10n_ch_weekly_lessons and not current_contract.irregular_working_time:
                        working_time["Steady"] = {
                            "WeeklyHoursAndLessons": hours_dict
                        }
                    else:
                        working_time["Steady"] = {
                            **hours_dict
                        }
                    working_time["Steady"]["ActivityRate"] = self._amount2str(current_contract.l10n_ch_current_occupation_rate)

                work["Work"] = {
                    "WorkingTime": working_time,
                    "EntryDate": format_date(self.env, current_contract.date_start, date_format='yyyy-MM-dd')
                }
                if last_withdrawal and (last_withdrawal > current_contract.date_start or last_withdrawal.month == snapshot.month and last_withdrawal.year == snapshot.year) and (last_withdrawal <= datetime.date(snapshot.year, snapshot.month, 1) + relativedelta(days=-1, months=1)):
                    work["Work"]["WithdrawalDate"] = format_date(self.env, last_withdrawal, date_format='yyyy-MM-dd')

            else:
                snapshot.person = False
                continue

            self._fill_xml_scheme(civil_status, "Status", employee._get_l10n_ch_declaration_marital(), True, res_model='hr.employee', res_id=employee.id, res_field="marital")
            self._fill_xml_scheme(civil_status, "ValidAsOf", employee.l10n_ch_marital_from, True, lambda d: format_date(self.env, d, date_format='yyyy-MM-dd'), res_model='hr.employee', res_id=employee.id, res_field="l10n_ch_marital_from")

            self._fill_xml_scheme(particular, "EmployeeNumber", employee.registration_number, True, res_model='hr.employee', res_id=employee.id, res_field="registration_number")
            self._fill_xml_scheme(particular, "Lastname", employee.l10n_ch_legal_last_name, True, res_model='hr.employee', res_id=employee.id, res_field="l10n_ch_legal_last_name")
            self._fill_xml_scheme(particular, "Firstname", employee.l10n_ch_legal_first_name, True, res_model='hr.employee', res_id=employee.id, res_field="l10n_ch_legal_first_name")
            self._fill_xml_scheme(particular, "Sex", employee.gender, True, lambda_f=lambda g: "M" if g == "male" else "F" if g == "female" else False, res_model='hr.employee', res_id=employee.id, res_field="gender")
            self._fill_xml_scheme(particular, "DateOfBirth", employee.birthday, True, lambda d: format_date(self.env, d, date_format='yyyy-MM-dd'), res_model='hr.employee', res_id=employee.id, res_field="birthday")
            self._fill_xml_scheme(particular, "Nationality", employee.country_id, True, lambda_f=lambda d: d.code if d else employee.l10n_ch_no_nationality or False, res_model='hr.employee', res_id=employee.id, res_field="country_id")
            self._fill_xml_scheme(particular, "ResidenceCanton", employee.l10n_ch_canton, True, res_model='hr.employee', res_id=employee.id, res_field="l10n_ch_canton")
            self._fill_xml_scheme(particular, "LanguageCode", employee.lang, True, lambda_f=lambda l: l[:2] if l else False, res_model='hr.employee', res_id=employee.id, res_field="lang")
            self._fill_xml_scheme(particular, "ResidenceCategory", employee.l10n_ch_residence_category, condition=employee.l10n_ch_has_withholding_tax and not employee.country_id.code == "CH", res_model='hr.employee', res_id=employee.id, res_field="l10n_ch_residence_category")
            self._fill_xml_scheme(particular, "MunicipalityID", employee.l10n_ch_municipality if employee.l10n_ch_canton != 'EX' else False, condition=employee.l10n_ch_has_withholding_tax and employee.l10n_ch_canton != 'EX', res_model='hr.employee', res_id=employee.id, res_field="l10n_ch_municipality")

            particular.update({
                "CivilStatus": civil_status,
                **address,
                **social_insurance_identification
            })

            snapshot.person = {
                "Particulars": particular,
                **work
            }

    @api.depends("employee_id", "year", "month")
    def _compute_bvg_lpp_annual_basis(self):
        swissdec_structure_rules = self.env.ref('l10n_ch_hr_payroll_elm_transmission.hr_payroll_structure_ch_elm').rule_ids
        paid_slips = self.env["hr.payslip"]._read_group(
            domain=[("employee_id", 'in', self.employee_id.ids),
                    ('l10n_ch_lpp_not_insured', '!=', True),
                    ('l10n_ch_compensation_fund_id', '!=', False),
                    ("state", "in", ["paid", "done"]),
                    ('struct_id.code', '=', 'CHMONTHLYELM')],
            groupby=["employee_id", "date_to:year", "date_to:month"],
            aggregates=["id:recordset"])

        rule_codes = swissdec_structure_rules.mapped('code')
        retroactive_rules = swissdec_structure_rules.filtered(lambda r: r.l10n_ch_lpp_retroactive)
        previsional_rules = swissdec_structure_rules.filtered(lambda r: r.l10n_ch_lpp_forecast)

        declared_bvg_lpp_basis = self.env["l10n.ch.lpp.basis.report"]._read_group(domain=[], groupby=['company_id', 'year', 'month'], aggregates=["id:recordset"])
        mapped_bvg_lpp_declarations = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: self.env["l10n.ch.lpp.basis.report"]))))
        for comp, year, month, declaration in declared_bvg_lpp_basis:
            mapped_bvg_lpp_declarations[comp][year][int(month)] = declaration

        line_values = self.env["hr.payslip"].search(
            [("employee_id", 'in', self.employee_id.ids), ("state", "in", ["paid", "done"]), ('struct_id.code', '=', 'CHMONTHLYELM')])._get_line_values(rule_codes)

        mapped_payslips = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: self.env["hr.payslip"])))

        for emp, date_y, date_m, slip in paid_slips:
            mapped_payslips[emp][date_y.year][date_m.month] += slip.filtered(
                lambda p: not p.l10n_ch_after_departure_payment)

        for emp, date_y, date_m, slips in paid_slips:
            for slip in slips:
                if slip.l10n_ch_after_departure_payment:
                    latest_preceding_slip = None
                    for year, months in mapped_payslips[emp].items():
                        for month, month_slips in months.items():
                            relevant_slips = month_slips.filtered(
                                lambda p: not p.l10n_ch_after_departure_payment and p.date_to <= slip.date_from
                            )
                            if relevant_slips:
                                candidate = max(relevant_slips, key=lambda p: p.date_to)
                                if not latest_preceding_slip or candidate.date_to > latest_preceding_slip.date_to:
                                    latest_preceding_slip = candidate

                    if latest_preceding_slip:
                        target_year = latest_preceding_slip.date_to.year
                        target_month = latest_preceding_slip.date_to.month
                        mapped_payslips[emp][target_year][target_month] += slip
                    else:
                        mapped_payslips[emp][date_y.year][date_m.month] += slip


        for snapshot in self:
            existing_declaration = [r for m, r in mapped_bvg_lpp_declarations[snapshot.employee_id.company_id][snapshot.year].items() if r]
            existing_declaration = max(existing_declaration, key=lambda r: r[0].month) if existing_declaration else False
            existing_employee_declaration = False
            if existing_declaration:
                lpp_line = existing_declaration.lpp_basis_line_ids.filtered(lambda l: l.employee_id == snapshot.employee_id)
                if lpp_line:
                    existing_employee_declaration = lpp_line.lpp_declared_basis
            if existing_employee_declaration:
                snapshot.bvg_lpp_annual_basis = existing_employee_declaration
            else:
                presumable_current_month_slip = mapped_payslips[snapshot.employee_id][snapshot.year][snapshot.month]
                retroactive_payslips = mapped_payslips[snapshot.employee_id][snapshot.year - 1]
                if presumable_current_month_slip:
                    as_days_n_1 = sum([line_values['ASDAYS'][slip.id]['total'] for month, slips in retroactive_payslips.items() for slip in slips])
                    if as_days_n_1:
                        retroactive_basis = sum(line_values[r.code][slip.id]['total'] for month, slips in retroactive_payslips.items() for slip in slips for r in retroactive_rules) * 360 / as_days_n_1
                    else:
                        retroactive_basis = 0
                    previsional_basis = sum(line_values[r.code][p.id]['total'] * r.l10n_ch_lpp_factor for p in presumable_current_month_slip for r in previsional_rules)

                    total = float_round(retroactive_basis + previsional_basis, precision_rounding=0.01, rounding_method="HALF-UP")
                    if total % 0.05 >= 0.025:
                        total = total + 0.05 - (total % 0.05)
                    else:
                        total = total - (total % 0.05)

                    snapshot.bvg_lpp_annual_basis = total
                else:
                    snapshot.bvg_lpp_annual_basis = 0

    @api.depends("month", "year", "employee_id", "employee_meta_data")
    def _compute_additional_particular(self):
        for snapshot in self:
            additional_particular = {}
            current_employee = snapshot.employee_id
            if current_employee.l10n_ch_tax_code:
                self._fill_xml_scheme(additional_particular, "Denomination", current_employee.l10n_ch_religious_denomination, True, res_model='hr.employee', res_id=current_employee.id, res_field="l10n_ch_religious_denomination")

                if current_employee.l10n_ch_other_employment and current_employee.l10n_ch_total_activity_type == 'percentage':
                    other_activities = {
                        "TotalActivityRate": self._amount2str(current_employee.l10n_ch_other_activity_percentage)
                    }
                    additional_particular["OtherActivities"] = other_activities

                if (current_employee._get_l10n_ch_declaration_marital() not in ["married", "registeredPartnership"] and current_employee.children > 0 and current_employee.l10n_ch_tax_scale_type == "TaxAtSourceCode" and current_employee.l10n_ch_tax_scale in ['H', 'P', 'U']):
                    if current_employee.l10n_ch_concubinage == "NoConcubinage":
                        self._fill_xml_scheme(additional_particular, "SingleParentFamily", {"NoConcubinage": XSD_SKIP_VALUE}, True)
                    else:
                        self._fill_xml_scheme(additional_particular, "SingleParentFamily", {"Concubinage": {current_employee.l10n_ch_concubinage: XSD_SKIP_VALUE}}, True, lambda_f=lambda v: v if current_employee.l10n_ch_concubinage else False, res_model='hr.employee', res_id=current_employee.id, res_field="l10n_ch_concubinage")
                marriage_partner = {}
                if current_employee._get_l10n_ch_declaration_marital() in ["married", "registeredPartnership"]:
                    social_insurance_identification = {
                        "Social-InsuranceIdentification": {
                            "SV-AS-Number": current_employee.l10n_ch_spouse_sv_as_number
                        } if current_employee.l10n_ch_spouse_sv_as_number else {
                            "unknown": XSD_SKIP_VALUE
                        }
                    }
                    self._fill_xml_scheme(marriage_partner, "Firstname", current_employee.l10n_ch_spouse_first_name, True, res_model='hr.employee', res_id=current_employee.id, res_field="l10n_ch_spouse_first_name")
                    self._fill_xml_scheme(marriage_partner, "Lastname", current_employee.l10n_ch_spouse_last_name, True, res_model='hr.employee', res_id=current_employee.id, res_field="l10n_ch_spouse_last_name")
                    self._fill_xml_scheme(marriage_partner, "DateOfBirth", current_employee.l10n_ch_spouse_birthday, True, lambda_f=lambda bd: format_date(self.env, bd, date_format='yyyy-MM-dd'), res_model='hr.employee', res_id=current_employee.id, res_field="l10n_ch_spouse_birthday")
                    marriage_partner_address = {}
                    self._fill_xml_scheme(marriage_partner_address, "ZIP-Code", current_employee.l10n_ch_spouse_zip, True, res_model='hr.employee', res_id=current_employee.id, res_field="l10n_ch_spouse_zip")
                    self._fill_xml_scheme(marriage_partner_address, "City", current_employee.l10n_ch_spouse_city, True, res_model='hr.employee', res_id=current_employee.id, res_field="l10n_ch_spouse_city")
                    self._fill_xml_scheme(marriage_partner_address, "Country", current_employee.with_context(lang='en_US').l10n_ch_spouse_country_id, lambda_f=lambda c: c.name.upper())
                    self._fill_xml_scheme(marriage_partner_address, "Street", current_employee.l10n_ch_spouse_street)
                    self._fill_xml_scheme(
                        marriage_partner,
                        code="Residence",
                        value=current_employee,
                        condition=True,
                        lambda_f=lambda e: {"CantonCH": e.l10n_ch_spouse_residence_canton}
                                           if e.l10n_ch_spouse_residence_canton not in [False, "EX"]
                                           else {"AbroadCountry": e.l10n_ch_spouse_country_id.code}
                                           if e.l10n_ch_spouse_country_id
                                           else False,
                        res_model="hr.employee",
                        res_id=current_employee.id,
                        res_field="l10n_ch_spouse_residence_canton" if not current_employee.l10n_ch_spouse_residence_canton else "l10n_ch_spouse_country_id"
                    )

                    if current_employee.l10n_ch_spouse_revenues:
                        work_or_compensatory = {}
                        self._fill_xml_scheme(work_or_compensatory, "Workplace", current_employee.l10n_ch_spouse_work_canton, True, res_model='hr.employee', res_id=current_employee.id, res_field="l10n_ch_spouse_work_canton")
                        self._fill_xml_scheme(work_or_compensatory, "Start", current_employee.l10n_ch_spouse_work_start_date, True, lambda_f=lambda bd: format_date(self.env, bd, date_format='yyyy-MM-dd'), res_model='hr.employee', res_id=current_employee.id, res_field="l10n_ch_spouse_work_start_date")
                        self._fill_xml_scheme(work_or_compensatory, "Start", current_employee.l10n_ch_spouse_work_end_date, lambda_f=lambda bd: format_date(self.env, bd, date_format='yyyy-MM-dd'))
                        marriage_partner.update({
                            "WorkOrCompensatory": work_or_compensatory
                        })

                    marriage_partner.update({
                        "Address": marriage_partner_address
                    })
                    additional_particular.update({
                        "MarriagePartner": {
                            **marriage_partner,
                            **social_insurance_identification
                    }})
                children = []
                for child in current_employee.l10n_ch_children:
                    child_info = dict()
                    self._fill_xml_scheme(child_info, "Lastname", child.last_name, True, res_model='l10n.ch.hr.employee.children', res_id=child.id, res_field="last_name")
                    self._fill_xml_scheme(child_info, "Firstname", child.name, True, res_model='l10n.ch.hr.employee.children', res_id=child.id, res_field="name")
                    self._fill_xml_scheme(child_info, "DateOfBirth", child.birthdate, True, lambda_f=lambda c: format_date(self.env, c, date_format='yyyy-MM-dd'), res_model='l10n.ch.hr.employee.children', res_id=child.id, res_field="birthdate")
                    self._fill_xml_scheme(child_info, "Start", child.deduction_start, True, lambda_f=lambda c: format_date(self.env, c, date_format='yyyy-MM-dd'),  res_model='l10n.ch.hr.employee.children', res_id=child.id, res_field="deduction_start")
                    self._fill_xml_scheme(child_info, "End", child.deduction_end, False, lambda_f=lambda c: format_date(self.env, c, date_format='yyyy-MM-dd'))
                    children.append(child_info)
                if children:
                    additional_particular.update({
                        "Children": children
                    })
            snapshot.additional_particular = additional_particular

    def dict_diff(self, previous, current, path=""):
        differences = {}

        all_keys = set(previous.keys()).union(set(current.keys()))

        for key in all_keys:
            current_path = f"{path}.{key}" if path else key

            if key in previous and key in current:
                if isinstance(previous[key], dict) and isinstance(current[key], dict):
                    nested_diff = self.dict_diff(previous[key], current[key], current_path)
                    if nested_diff:
                        differences.update(nested_diff)
                elif previous[key] != current[key]:
                    differences[current_path] = {"previous": previous[key], "current": current[key]}
            elif key in previous:
                differences[current_path] = {"previous": previous[key], "current": ""}
            elif key in current:
                differences[current_path] = {"previous": "", "current": current[key]}

        return differences

    @api.depends("month", "year", "employee_id")
    def _compute_monthly_statistics(self):
        swissdec_declaration = SwissdecDeclaration()
        swissdec_structure_rules = self.env.ref('l10n_ch_hr_payroll_elm_transmission.hr_payroll_structure_ch_elm').rule_ids
        paid_slips = self.env["hr.payslip"]._read_group(
            domain=[
                ("employee_id", 'in', self.employee_id.ids),
                ("state", "in", ["paid", "done"]),
                ('struct_id.code', '=', 'CHMONTHLYELM'),
                ('l10n_ch_social_insurance_id', '!=', False),
                ('l10n_ch_laa_group', '!=', False),
                ('l10n_ch_location_unit_id', '!=', False),
                ('l10n_ch_compensation_fund_id', '!=', False),
            ],
            groupby=["employee_id", "date_to:year", "date_to:month"],
            aggregates=["id:recordset"])
        rule_codes = swissdec_structure_rules.mapped('code')
        rules_grouped_by_monthly_statistic = swissdec_structure_rules.filtered(lambda r: r.l10n_ch_wage_statement).grouped('l10n_ch_wage_statement')
        rules_grouped_by_yearly_statistic = swissdec_structure_rules.filtered(lambda r: r.l10n_ch_yearly_statement).grouped('l10n_ch_yearly_statement')

        line_values = self.env["hr.payslip"].search(
            [("employee_id", 'in', self.employee_id.ids), ("state", "in", ["paid", "done"]), ('struct_id.code', '=', 'CHMONTHLYELM')])._get_line_values(
            rule_codes)


        mapped_payslips = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: self.env["hr.payslip"])))

        for emp, date_y, date_m, slip in paid_slips:
            mapped_payslips[emp][date_y.year][date_m.month] += slip.filtered(lambda p: not p.l10n_ch_after_departure_payment)

        for snapshot in self:
            relevant_payslips = mapped_payslips[snapshot.employee_id][snapshot.year]
            relevant_monthly_payslips = relevant_payslips[snapshot.month]
            if relevant_monthly_payslips:
                last_monthly_payslip = relevant_monthly_payslips.sorted("date_to")[-1]
                relevant_contract = last_monthly_payslip.contract_id
                statistic_salary = {
                    "CurrentMonth": [XSD_YMONTH, snapshot.year, snapshot.month, False],
                    "institutionIDRef": "#BFS"
                }
                self._fill_xml_scheme(statistic_salary, "workplaceIDRef", swissdec_declaration.get_workplace_id_ref(last_monthly_payslip.l10n_ch_location_unit_id), True)
                additional_particular = dict()

                self._fill_xml_scheme(additional_particular, "Position", relevant_contract.l10n_ch_job_type, True)
                self._fill_xml_scheme(additional_particular, "Education", snapshot.employee_id.certificate, True, lambda_f=lambda c: c if c in ALLOWED_EDUCATION else "mandatorySchoolOnly")
                self._fill_xml_scheme(additional_particular, "JobTitle", relevant_contract.job_id.name, True)
                self._fill_xml_scheme(additional_particular, "LeaveEntitlement", relevant_contract.l10n_ch_yearly_holidays, True, lambda_f=lambda l: l or "0")
                self._fill_xml_scheme(additional_particular, "PermanentStaffPublicAdmin", last_monthly_payslip.contract_id.l10n_ch_permanent_staff_public_admin, condition=False, lambda_f=lambda v: XSD_SKIP_VALUE if v else False)
                self._fill_xml_scheme(additional_particular, "TemporaryAgencyWorker", last_monthly_payslip.contract_id.l10n_ch_interim_worker, condition=False, lambda_f=lambda v: XSD_SKIP_VALUE if v else False)
                self._fill_xml_scheme(additional_particular, "FlexProfiling", snapshot.employee_id.l10n_ch_flex_profiling, condition=False)
                statistic_salary["AdditionalParticulars"] = additional_particular
                kind_of_wage_payment = dict()
                working_time = swissdec_declaration.get_workplace_working_hours(last_monthly_payslip.l10n_ch_location_unit_id)
                contractual_13_14 = []
                if relevant_contract.l10n_ch_thirteen_month:
                    contractual_13_14.append(self._amount2str(relevant_contract.l10n_ch_contractual_13th_month_rate))
                if relevant_contract.l10n_ch_14th_month:
                    contractual_13_14.append(self._amount2str(relevant_contract.l10n_ch_contractual_13th_month_rate))

                if relevant_contract.wage_type == "monthly":
                    kind_of_wage_payment["Monthly"] = dict()

                    self._fill_xml_scheme(kind_of_wage_payment["Monthly"], "Contract", relevant_contract.contract_type_id.code, True)
                    self._fill_xml_scheme(kind_of_wage_payment["Monthly"], "ContractualMonthlyWage", relevant_monthly_payslips, True, lambda_f= lambda slips: self._amount2str(sum(line_values["WT_1000"][p.id]["total"] for p in slips)))
                    self._fill_xml_scheme(kind_of_wage_payment["Monthly"], "Contractual13th", contractual_13_14, True, lambda_f=lambda c: c if c else "0.00")
                    self._fill_xml_scheme(kind_of_wage_payment["Monthly"], "ActivityRate", relevant_contract, True, lambda_f= lambda c: self._amount2str(c.l10n_ch_current_occupation_rate))
                    monthly_working_time = dict()
                    if "WeeklyHours" in working_time:
                        monthly_working_time["WeeklyHours"] = {
                            "_value_1": self._amount2str(relevant_contract.l10n_ch_weekly_hours),
                            "companyWeeklyHoursIDRef": working_time['WeeklyHours']["companyWeeklyHoursID"]
                        }
                    elif "WeeklyLessons" in working_time:
                        monthly_working_time["WeeklyHours"] = {
                            "_value_1": self._amount2str(relevant_contract.l10n_ch_weekly_lessons),
                            "companyWeeklyLessonsIDRef": working_time['WeeklyLessons']["companyWeeklyLessonsID"]
                        }
                    elif "WeeklyHoursAndLessons" in working_time:
                        monthly_working_time["WeeklyHoursAndLessons"] = dict()
                        monthly_working_time["WeeklyHoursAndLessons"]["WeeklyHours"] = self._amount2str(relevant_contract.l10n_ch_weekly_hours)
                        monthly_working_time["WeeklyHoursAndLessons"]["WeeklyLessons"] = self._amount2str(relevant_contract.l10n_ch_weekly_lessons)
                        monthly_working_time["WeeklyHoursAndLessons"]["companyWeeklyHoursAndLessonsIDRef"] = working_time["WeeklyHoursAndLessons"]["companyWeeklyHoursAndLessonsID"]
                    kind_of_wage_payment["Monthly"]["WorkingTime"] = monthly_working_time

                elif relevant_contract.wage_type == "hourly":
                    kind_of_wage_payment["Hourly"] = {
                        "ContractualHourlyWage": dict()
                    }

                    salary = dict()
                    self._fill_xml_scheme(kind_of_wage_payment["Hourly"], "Contract", relevant_contract.contract_type_id.code, True)
                    self._fill_xml_scheme(salary, "PaidByHour", relevant_contract, True, lambda_f=lambda c: self._amount2str(c.hourly_wage))
                    self._fill_xml_scheme(salary, "PaidByLesson", relevant_contract, True, lambda_f=lambda c: self._amount2str(c.l10n_ch_lesson_wage))
                    kind_of_wage_payment["Hourly"]["ContractualHourlyWage"]["Salary"] = salary
                    self._fill_xml_scheme(kind_of_wage_payment["Hourly"]["ContractualHourlyWage"], "Vacation", relevant_contract, True, lambda_f=lambda c: self._amount2str(c.l10n_ch_contractual_holidays_rate))
                    self._fill_xml_scheme(kind_of_wage_payment["Hourly"]["ContractualHourlyWage"], "PublicHolidayCompensation", relevant_contract, True, lambda_f=lambda c: self._amount2str(c.l10n_ch_contractual_public_holidays_rate))
                    self._fill_xml_scheme(kind_of_wage_payment["Hourly"]["ContractualHourlyWage"], "Contractual13th", contractual_13_14, True, lambda_f=lambda c: c if c else "0.00")

                    totally_worked = dict()
                    total_hours_worked = self._amount2str(sum(relevant_monthly_payslips.line_ids.filtered(lambda pl: pl.code == "BASICHOURLY").mapped("rate"))/100)
                    total_lessons_worked = self._amount2str(sum(relevant_monthly_payslips.line_ids.filtered(lambda pl: pl.code == "BASICLESSON").mapped("rate"))/100)
                    if "WeeklyHours" in working_time:
                        totally_worked["TotalHoursOfWork"] = {
                            "_value_1": total_hours_worked,
                            "companyWeeklyHoursIDRef": working_time['WeeklyHours']["companyWeeklyHoursID"]
                        }
                    elif "WeeklyLessons" in working_time:
                        totally_worked["TotalLessonsOfWork"] = {
                            "_value_1": total_lessons_worked,
                            "companyWeeklyLessonsIDRef": working_time['WeeklyLessons']["companyWeeklyLessonsID"]
                        }
                    elif "WeeklyHoursAndLessons" in working_time:
                        totally_worked["TotalHoursAndLessonsOfWork"] = dict()
                        totally_worked["TotalHoursAndLessonsOfWork"]["TotalHoursOfWork"] = total_hours_worked
                        totally_worked["TotalHoursAndLessonsOfWork"]["TotalLessonsOfWork"] = total_lessons_worked
                        totally_worked["TotalHoursAndLessonsOfWork"]["companyWeeklyHoursAndLessonsIDRef"] = working_time["WeeklyHoursAndLessons"]["companyWeeklyHoursAndLessonsID"]
                    kind_of_wage_payment["Hourly"]["TotallyWorked"] = totally_worked

                elif relevant_contract.wage_type == "NoTimeConstraint":
                    kind_of_wage_payment["NoTimeConstraint"] = dict()
                    self._fill_xml_scheme(kind_of_wage_payment["NoTimeConstraint"], "Contract", relevant_contract.contract_type_id.code, True)
                    self._fill_xml_scheme(kind_of_wage_payment["NoTimeConstraint"], "ContractualAnnualWage", relevant_contract, True, lambda_f=lambda c: self._amount2str(c.l10n_ch_contractual_annual_wage))
                    self._fill_xml_scheme(kind_of_wage_payment["NoTimeConstraint"], "Vacation", relevant_contract.l10n_ch_contractual_holidays_rate, False, lambda_f=lambda c: self._amount2str(c))
                    self._fill_xml_scheme(kind_of_wage_payment["NoTimeConstraint"], "PublicHolidayCompensation", relevant_contract.l10n_ch_contractual_public_holidays_rate, False, lambda_f=lambda c: self._amount2str(c))
                    self._fill_xml_scheme(kind_of_wage_payment["NoTimeConstraint"], "Contractual13th", contractual_13_14, False, lambda_f=lambda c: c if c else "0.00")

                    if not relevant_contract.irregular_working_time:
                        self._fill_xml_scheme(kind_of_wage_payment["NoTimeConstraint"], "ActivityRate", relevant_contract, True, lambda_f=lambda c: self._amount2str(c.l10n_ch_current_occupation_rate))
                        ntc_working_time = dict()
                        if "WeeklyHours" in working_time:
                            ntc_working_time["WeeklyHours"] = {
                                "_value_1": self._amount2str(relevant_contract.l10n_ch_weekly_hours),
                                "companyWeeklyHoursIDRef": working_time['WeeklyHours']["companyWeeklyHoursID"]
                            }
                            ntc_working_time["companyWeeklyHoursIDRef"] = working_time['WeeklyHours']["companyWeeklyHoursID"]
                        elif "WeeklyLessons" in working_time:
                            ntc_working_time["WeeklyHours"] = {
                                "_value_1": self._amount2str(relevant_contract.l10n_ch_weekly_lessons),
                                "companyWeeklyLessonsIDRef": working_time['WeeklyLessons']["companyWeeklyLessonsID"]
                            }
                        elif "WeeklyHoursAndLessons" in working_time:
                            ntc_working_time["WeeklyHoursAndLessons"] = dict()
                            ntc_working_time["WeeklyHoursAndLessons"]["WeeklyHours"] = self._amount2str(relevant_contract.l10n_ch_weekly_hours)
                            ntc_working_time["WeeklyHoursAndLessons"]["WeeklyLessons"] = self._amount2str(relevant_contract.l10n_ch_weekly_lessons)
                            ntc_working_time["WeeklyHoursAndLessons"]["companyWeeklyHoursAndLessonsIDRef"] = working_time["WeeklyHoursAndLessons"]["companyWeeklyHoursAndLessonsID"]

                        kind_of_wage_payment["NoTimeConstraint"]["WorkingTime"] = ntc_working_time

                statistic_salary["KindOfWagePayment"] = kind_of_wage_payment

                monthly_values = {
                    STATISTICS_RULE_MAPPING["Monthly"][s_section]: "0.00" for s_section in STATISTICS_RULE_MAPPING["Monthly"]
                }
                for s_section in STATISTICS_RULE_MAPPING["Monthly"]:
                    amnt = sum(line_values[rule.code][p.id]["total"] for p in relevant_monthly_payslips for rule in rules_grouped_by_monthly_statistic[s_section])
                    monthly_values[STATISTICS_RULE_MAPPING["Monthly"][s_section]] = self._amount2str(amnt)

                yearly_values = []
                relevant_slip_period = self.env["hr.payslip"]
                for month in range(1, snapshot.month + 1):
                    relevant_slip_period += relevant_payslips[month]

                slips_grouped_by_contract = relevant_slip_period.grouped("contract_id")

                for contract in slips_grouped_by_contract:
                    contract_slips = slips_grouped_by_contract[contract]
                    start_period = max(max(datetime.date(snapshot.year, 1, 1), contract.date_start),
                                    min(contract_slips.mapped('date_from')))
                    eom = datetime.date(snapshot.year, snapshot.month, 1) + relativedelta(months=1, days=-1)
                    end_period = min(min(eom, contract.date_end) if contract.date_end else eom,
                                  max(contract_slips.mapped('date_to')))

                    period_values = {
                        "Period": {
                            "from": format_date(self.env, start_period, date_format='yyyy-MM-dd'),
                            "until": format_date(self.env, end_period, date_format='yyyy-MM-dd')
                        },
                        **{STATISTICS_RULE_MAPPING["Annual"][s_section]: "0.00" for s_section in STATISTICS_RULE_MAPPING["Annual"]}
                    }
                    for s_section in STATISTICS_RULE_MAPPING["Annual"]:
                        amnt = sum(line_values[rule.code][p.id]["total"] for p in contract_slips for rule in rules_grouped_by_yearly_statistic[s_section])
                        period_values[STATISTICS_RULE_MAPPING["Annual"][s_section]] = self._amount2str(amnt)

                    yearly_values.append(period_values)


                statistic_salary["MonthlyValues"] = monthly_values
                statistic_salary["AnnualValues"] = yearly_values
                snapshot.monthly_statistics = {
                    "StatisticSalaries": {
                        "StatisticSalary": [statistic_salary]
                    }
                }
            else:
                snapshot.monthly_statistics = False

    @api.depends("month", "year", "employee_id")
    def _compute_mutations(self):
        paid_slips = self.env["hr.payslip"]._read_group(
            domain=[("employee_id", 'in', self.employee_id.ids),
                    ("l10n_ch_is_correction", '!=', False),
                    ("state", "in", ["paid", "done"]),
                    ('struct_id.code', '=', 'CHMONTHLYELM')],
            groupby=["employee_id", "date_to:year", "date_to:month"],
            aggregates=["id:recordset"])

        mapped_contracts = dict(self.env["hr.contract"]._read_group(domain=[
            ('state', 'in', ['open', 'close']),
        ], groupby=["employee_id"],
            aggregates=["id:recordset"]
        ))

        mapped_corrections = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: self.env["hr.employee.is.line"])))
        for emp, date_y, date_m, slip in paid_slips:
            if slip.l10n_ch_is_correction.state == "confirmed":
                mapped_corrections[emp][date_y.year][date_m.month] += slip.l10n_ch_is_correction
        mapped_snapshots = self.env['l10n.ch.employee.yearly.values']._get_mapped_snapshots(domain=[('employee_id', 'in', self.mapped('employee_id').ids)])

        self.mapped('is_mutations').filtered(lambda m: m.auto_generated).unlink()
        self.mapped('lpp_mutations').filtered(lambda m: m.auto_generated).unlink()

        for snapshot in self:
            is_vals = []
            lpp_vals = []

            year_sub = 1 if snapshot.month == 1 else 0
            valid_source_tax_snapshot = mapped_snapshots[snapshot.employee_id][snapshot.year - year_sub][(snapshot.month - 2) % 12 + 1]

            if valid_source_tax_snapshot and snapshot.employee_meta_data:
                current_st_canton = snapshot.employee_meta_data.get('st-canton', False)
                current_st_municipality = snapshot.employee_meta_data.get('st-municipality', False)

                correction_mutations = mapped_corrections[snapshot.employee_id][snapshot.year][snapshot.month]
                confirmed_st_mutations = {
                    mutation.reason: mutation for mutation in correction_mutations.mapped('is_ema_ids')
                }

                entries = mapped_contracts.get(snapshot.employee_id, self.env['hr.contract']).filtered(lambda c: c.date_start.month == snapshot.month and c.date_start.year == snapshot.year).mapped("date_start")
                withdrawals = mapped_contracts.get(snapshot.employee_id, self.env['hr.contract']).filtered(lambda c: c.date_end and c.date_end.month == snapshot.month and c.date_end.year == snapshot.year).mapped("date_end")

                if entries or withdrawals:
                    if snapshot.employee_id.l10n_ch_has_withholding_tax:
                        for entry in entries:
                            is_vals += [(0, 0, {
                                "employee_id": snapshot.employee_id.id,
                                "reason": "entryCompany",
                                "qst_canton": current_st_canton,
                                "qst_municipality": current_st_municipality,
                                "valid_as_of": entry,
                                "auto_generated": True
                            })]
                        for withdrawal in withdrawals:
                            is_vals += [(0, 0, {
                                "employee_id": snapshot.employee_id.id,
                                "reason": "withdrawalCompany",
                                "qst_canton": current_st_canton,
                                "qst_municipality": current_st_municipality,
                                "valid_as_of": withdrawal,
                                "auto_generated": True
                            })]
                else:
                    previous_additional_particular = valid_source_tax_snapshot.additional_particular
                    previous_meta_data = valid_source_tax_snapshot.employee_meta_data
                    diff = {}
                    if previous_additional_particular and snapshot.additional_particular:
                        diff.update(snapshot.dict_diff(previous_additional_particular, snapshot.additional_particular))

                    if previous_meta_data and snapshot.employee_meta_data:
                        diff.update(snapshot.dict_diff(previous_meta_data, snapshot.employee_meta_data))

                    st_mutations = set()
                    lpp_mutation = set()
                    if valid_source_tax_snapshot.bvg_lpp_annual_basis and valid_source_tax_snapshot.bvg_lpp_annual_basis != snapshot.bvg_lpp_annual_basis:
                        lpp_mutation.add("changeSalary")

                    for key in diff:
                        if key == "Particulars.ResidenceCategory":
                            current_cat = diff[key]["current"] == "settled-C"
                            previous_cat = diff[key]["previous"]
                            if current_cat and previous_cat:
                                st_mutations.add("withdrawalSettled")
                        if key == "Particulars.Nationality":
                            current_cat = diff[key]["current"] == "CH"
                            previous_cat = diff[key]["previous"] and diff[key]["previous"] != "CH"
                            if current_cat and previous_cat:
                                st_mutations.add("withdrawalNat")
                        if key == "st-canton":
                            current_cat = diff[key]["current"]
                            previous_cat = diff[key]["previous"]
                            if current_cat and previous_cat:
                                st_mutations.add(f"entryCanton-{current_cat}-{snapshot.employee_meta_data.get('st-municipality', '')}")
                                st_mutations.add(f"withdrawalCanton-{previous_cat}-{previous_meta_data.get('st-municipality', '')}")
                        if key.startswith("Particulars.Address"):
                            st_mutations.add("residence")
                            lpp_mutation.add("residence")
                        if key == "MarriagePartner" or key == "Particulars.CivilStatus.Status":
                            st_mutations.add("civilstate")
                            lpp_mutation.add("civilstate")
                            if snapshot.additional_particular:
                                if snapshot.additional_particular.get("MarriagePartner", dict()).get("WorkOrCompensatory", False):
                                    st_mutations.add("partnerWork")
                        if key == "MarriagePartner.WorkOrCompensatory.Workplace":
                            previous_ex = diff[key]["current"] == "EX"
                            current_ex = diff[key]["previous"] == "EX"
                            if previous_ex or current_ex:
                                st_mutations.add("partnerWorkplaceChangeCHAbroad")
                        if key == "MarriagePartner.WorkOrCompensatory":
                            st_mutations.add("partnerWork")
                        if key == "lpp_codes" and "lpp_institution" not in diff:
                            lpp_mutation.add("changeBVG-LPP-Code")
                        if key.startswith("Work.WorkingTime"):
                            lpp_mutation.add("activityRate")

                    previous_st_type_scale = previous_meta_data["st-type"] == "TaxAtSourceCode"
                    current_st_type_scale = snapshot.employee_meta_data["st-type"] == "TaxAtSourceCode"

                    if previous_st_type_scale and current_st_type_scale:
                        if previous_meta_data["children_deduction"] != snapshot.employee_meta_data["children_deduction"]:
                            st_mutations.add("childrenDeduction")

                    previous_st_code = previous_meta_data["st-code"]
                    current_st_code = snapshot.employee_meta_data["st-code"]
                    if previous_st_code and current_st_code:
                        if previous_st_code[-1] != current_st_code[-1]:
                            st_mutations.add("churchTax")
                    if snapshot.employee_id.l10n_ch_has_withholding_tax:
                        canton_change = False
                        for mutation in st_mutations:
                            if (mutation.startswith('withdrawalCanton') or mutation.startswith('entryCanton')) and ('withdrawalNat' in st_mutations or 'withdrawalSettled' in st_mutations):
                                continue
                            if mutation.startswith('withdrawalCanton'):
                                reason = "withdrawalCanton"
                                canton_change = True
                            elif mutation.startswith('entryCanton'):
                                reason = "entryCanton"
                                canton_change = True
                            else:
                                reason = mutation
                            if reason not in confirmed_st_mutations:
                                validity_date = datetime.date(snapshot.year, snapshot.month, 1)
                                if reason in ["withdrawalNat", "withdrawalSettled"]:
                                    validity_date += relativedelta(months=1, days=-1)
                                elif reason == "withdrawalCanton":
                                    validity_date += relativedelta(days=-1)

                                is_vals += [(0, 0, {
                                    "employee_id": snapshot.employee_id.id,
                                    "reason": reason,
                                    "qst_canton": mutation.split('-')[1] if canton_change else current_st_canton,
                                    "qst_municipality": mutation.split('-')[2] if canton_change else current_st_municipality,
                                    "valid_as_of": validity_date,
                                    "auto_generated": True
                                })]
                            canton_change = False

                    for mutation in lpp_mutation:
                        lpp_vals += [(0, 0, {
                            "employee_id": snapshot.employee_id.id,
                            "contract_id": snapshot.employee_id.contract_id.id,
                            "reason": mutation,
                            "valid_as_of": datetime.date(snapshot.year, snapshot.month, 1),
                            "auto_generated": True
                        })]


            snapshot.update({
                "is_mutations": is_vals,
                "lpp_mutations": lpp_vals,
            })

    def _find_structured_missing(self, d, result=None):
        """
        Recursively find dictionaries that have '_missing_' == True,
        and record them in 'result' with their path.
        """
        if result is None:
            result = []

        if isinstance(d, dict):
            if d.get("_missing_"):
                result.append(d)
            else:
                for key, value in d.items():
                    self._find_structured_missing(value, result)
        elif isinstance(d, list):
            for index, item in enumerate(d):
                self._find_structured_missing(item, result)
        return result

    @api.depends('employee_meta_data')
    def _compute_validation_errors(self):
        for snapshot in self:
            to_check = [snapshot.employee_meta_data]
            missing_entries = []
            for value in to_check:
                if value:
                    missing_entries.extend(self._find_structured_missing(value))

            snapshot_warnings = {}
            for missing_index, missing_dict in enumerate(missing_entries):
                res_model = missing_dict.get("res_model")
                res_id = missing_dict.get("res_id")
                res_field = missing_dict.get("res_field")
                if res_model and res_id:
                    record = self.env[res_model].browse(res_id)
                    field_description = self.env[res_model]._fields[res_field].get_description(self.env, ["string"])["string"]
                    snapshot_warnings[missing_index] = {
                        "message": _("Missing"),
                        "level": "warning",
                        "action": record._get_records_action(),
                        "action_text": field_description,
                    }

            snapshot.validation_errors = snapshot_warnings
