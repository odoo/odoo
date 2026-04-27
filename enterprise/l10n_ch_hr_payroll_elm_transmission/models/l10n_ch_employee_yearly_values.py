# Part of Odoo. See LICENSE file for full copyright and licensing details.
import datetime
from collections import defaultdict

from odoo import _, api, fields, models, Command
from odoo.tools.misc import format_date, file_path
from ..api.swissdec_declarations import SwissdecDeclaration, SwissdecInstitution
from odoo.exceptions import ValidationError

from dateutil.relativedelta import relativedelta
import uuid

XSD_SKIP_VALUE = "XSDSKIP"
MISSING_VALUE = "XSDMISSING"
XSD_YMONTH = "XSDGYEARMONTH"

CERTIFICATE_RULE_MAPPING = {
    '1': 'Income',
    '2.1': 'FringeBenefits/FoodLodging',
    '2.2': 'FringeBenefits/CompanyCar',
    '2.3': 'FringeBenefits/Other',
    '3': 'SporadicBenefits',
    '4': 'CapitalPayment',
    '5': 'OwnershipRight',
    '6': 'BoardOfDirectorsRemuneration',
    '7': 'OtherBenefits',
    '9': 'AHV-ALV-NBUV-AVS-AC-AANP-Contribution',
    '10.1': 'BVG-LPP-Contribution/Regular',
    '10.2': 'BVG-LPP-Contribution/Purchase',
    '11': 'NetIncome',
    '12': 'DeductionAtSource',
    '13': 'Charges',
    '13.1': 'Charges/Effective',
    '13.1.1': 'Charges/Effective/TravelFoodAccommodation',
    '13.1.2': 'Charges/Effective/Other',
    '13.2': 'Charges/LumpSum',
    '13.2.1': 'Charges/LumpSum/Representation',
    '13.2.2': 'Charges/LumpSum/Car',
    '13.2.3': 'Charges/LumpSum/Other',
    '13.3': 'Charges/Education',
    '14': 'OtherFringeBenefits',
}

ANNUITY_RULE_MAPPING = {
    '1': 'Income',
    '2.3': 'FringeBenefits',
    '3': 'SporadicBenefits',
    '5': 'OwnershipRight',
    '7': 'OtherBenefits',
    '11': 'NetIncome',
    '12': 'DeductionAtSource',
    '14': 'OtherFringeBenefits',
}

IS_REASON_MAPPING = {
    'entryCompany': ('Entry', 'entryCompany'),
    'entryCanton': ('Entry', 'cantonChange'),
    'entryOther': ('Entry', 'entryOther'),
    'withdrawalCompany': ('Withdrawal', 'withdrawalCompany'),
    'withdrawalNat': ('Withdrawal', 'naturalization'),
    'withdrawalSettled': ('Withdrawal', 'settled-C'),
    'withdrawalCanton': ('Withdrawal', 'cantonChange'),
    'withdrawalOther': ('Withdrawal', 'others'),
    'civilstate': ('Mutation', 'civilstate'),
    'partnerWork': ('Mutation', 'partnerWork'),
    'partnerWorkplaceChangeCHAbroad': ('Mutation', 'partnerWorkplaceChangeCHAbroad'),
    'residence': ('Mutation', 'residence'),
    'childrenDeduction': ('Mutation', 'childrenDeduction'),
    'churchTax': ('Mutation', 'churchTax'),
    'others': ('Mutation', 'others')
}

QST_MAPPING = {
    "IS": "TaxAtSource",
    "ISSALARY": "TaxableEarning",
    "ISDTSALARY": "AscertainedTaxableEarning",
    "ISDTSALARYAPERIODIC": "SporadicBenefits"
}

def _structured_missing(model_name, res_id, field_name, field_label):
    """
    Return a dictionary marking a value as missing, with references
    so we can create an 'action' in your widget to fix it.
    """
    return {
        "_missing_": True,
        "model": model_name or "",
        "res_id": res_id or False,
        "field_name": field_name or "",
        "field_label": field_label or "",
    }

class L10nCHEmployeeYearlySnapshot(models.Model):
    _name = "l10n.ch.employee.yearly.values"
    _description = "Swiss Employee yearly history"

    employee_id = fields.Many2one('hr.employee', ondelete="cascade", required=True)
    year = fields.Integer(required=True)

    yearly_prospective = fields.Json(string="LPP Yearly Prospective", compute="_compute_yearly_prospective", store=True)

    monthly_value_ids = fields.One2many('l10n.ch.employee.monthly.values', 'yearly_values_id', compute="_compute_monthly_value_ids", store=True)

    validation_errors = fields.Json(compute="_compute_validation_errors")

    _sql_constraints = [
        ('ch_yearly_snapshot_unique', 'unique(employee_id, year)', 'Yearly values for this employee already exists for the year.')
    ]

    @staticmethod
    def _amount2str(amount):
        return "{:.2f}".format(amount)

    @staticmethod
    def _fill_xml_scheme(dict, code, value, condition=False, lambda_f=lambda v: v):
        if value or condition:
            dict[code] = lambda_f(value) or MISSING_VALUE

    @staticmethod
    def _flat_dict_to_nest_dict(flat_dict):
        nested = lambda: defaultdict(nested)
        root = nested()

        for key, value in flat_dict.items():
            keys = key.split('/')
            d = root
            for part in keys[:-1]:
                d = d[part]
            d[keys[-1]] = value

        def to_dict(d):
            if isinstance(d, defaultdict):
                return {k: to_dict(v) for k, v in d.items()}
            return d

        return to_dict(root)

    def _toggle_pay_period_lock(self, lock=False):
        all_snapshots = self.monthly_value_ids
        if not all_snapshots:
            return

        domain = [
            ("employee_id", 'in', all_snapshots.mapped('employee_id').ids),
            ("state", "in", ["paid", "done"]),
            ('struct_id.code', '=', 'CHMONTHLYELM')
        ]

        paid_slips_data = self.env["hr.payslip"]._read_group(
            domain=domain,
            groupby=["employee_id", "date_to:year", "date_to:month"],
            aggregates=["id:recordset"]
        )

        max_month_per_year_map = defaultdict(int)

        for employee, date_year, date_month, slips in paid_slips_data:
            year_val = date_year.year
            month_val = date_month.month

            key = (employee.id, year_val)

            if month_val > max_month_per_year_map[key]:
                max_month_per_year_map[key] = month_val

        snapshots_to_lock = self.env['l10n.ch.employee.monthly.values']
        snapshots_to_unlock = self.env['l10n.ch.employee.monthly.values']

        for snapshot in all_snapshots:
            key = (snapshot.employee_id.id, snapshot.year)

            cutoff_month = max_month_per_year_map.get(key, 0)

            if snapshot.month <= cutoff_month:
                snapshots_to_lock += snapshot
            else:
                snapshots_to_unlock += snapshot

        if snapshots_to_lock:
            snapshots_to_lock.write({"payroll_month_closed": True})

        if snapshots_to_unlock:
            snapshots_to_unlock.write({"payroll_month_closed": False})

    @api.depends("year", "employee_id")
    def _compute_monthly_value_ids(self):
        for snapshot in self:
            if not snapshot.monthly_value_ids:
                snapshot.update({
                    'monthly_value_ids': [Command.create({
                        'month': i
                    }) for i in range(1, 13)]
                })

    @api.model
    def _get_mapped_snapshots(self, domain=None):
        previous_snapshots = self._read_group(domain=domain, groupby=["employee_id", "year"], aggregates=["id:recordset"])
        mapped_snapshots = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: self.env["l10n.ch.employee.monthly.values"])))
        for employee, year, snapshot in previous_snapshots:
            for monthly_values in snapshot.monthly_value_ids:
                mapped_snapshots[employee][year][monthly_values.month] = monthly_values

        return mapped_snapshots

    def _get_yearly_mapped_payslips(self, domain=None):
        swissdec_structure_rules = self.env.ref('l10n_ch_hr_payroll_elm_transmission.hr_payroll_structure_ch_elm').rule_ids
        rule_codes = swissdec_structure_rules.mapped('code')

        paid_slips = self.env["hr.payslip"]._read_group(
            domain=domain,
            groupby=["employee_id", "date_to:year", "date_to:month"],
            aggregates=["id:recordset"])

        to_compute_line_values = self.env["hr.payslip"]

        mapped_payslips = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: self.env["hr.payslip"])))
        for emp, date_y, date_m, slip in paid_slips:
            mapped_payslips[emp][date_y.year][date_m.month] += slip.filtered(lambda p: not p.l10n_ch_after_departure_payment)
            to_compute_line_values += slip.filtered(lambda p: not p.l10n_ch_after_departure_payment)

        for emp, date_y, date_m, slips in paid_slips:
            for slip in slips:
                if slip.l10n_ch_after_departure_payment:
                    latest_preceding_slip = None
                    for year, months in mapped_payslips[emp].items():
                        for month, month_slips in months.items():
                            relevant_slips = month_slips.filtered(lambda p: not p.l10n_ch_after_departure_payment and p.date_to <= slip.date_from)
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

                    to_compute_line_values += slip

        line_values = to_compute_line_values._get_line_values(rule_codes)

        return mapped_payslips, line_values

    def _get_monthly_tax_at_source(self, year, month, company_id):
        swissdec_declaration = SwissdecDeclaration()
        paid_slips = self.env["hr.payslip"]._read_group(
            domain=[
                ("company_id", '=', company_id.id),
                ("state", "in", ["paid", "done"]),
                ('struct_id.code', '=', 'CHMONTHLYELM'),
                ('l10n_ch_social_insurance_id', '!=', False),
                ('l10n_ch_laa_group', '!=', False),
                ('l10n_ch_location_unit_id', '!=', False),
                ('l10n_ch_compensation_fund_id', '!=', False),
            ],
            groupby=["employee_id", "date_to:year", "date_to:month"],
            aggregates=["id:recordset"])
        yearly_values = self.env["l10n.ch.employee.yearly.values"].search([("year", '=', year), ('employee_id.company_id', '=', company_id.id)])
        qst_institutions = self.env["l10n.ch.source.tax.institution"].search([('company_id', '=', company_id.id)])
        mapped_qst_institutions = qst_institutions.grouped("canton")

        source_tax_commission = defaultdict(float)

        for qst_institution in qst_institutions:
            commission_rate = self.env['hr.rule.parameter']._get_parameter_from_code(f'l10n_ch_withholding_tax_rates_{qst_institution.canton.upper()}_PEL', date=datetime.date(year, month, 1), raise_if_not_found=False)
            if commission_rate:
                # Format : [(1.0, 999999.0, 0.0, 2.0)]
                real_rate = commission_rate[0][3] / 100
            else:
                real_rate = 0
            source_tax_commission[swissdec_declaration.get_institution_id_ref(institution=qst_institution)] = real_rate


        qst_ema = self.env["l10n.ch.is.mutation"]._read_group(
            domain=[("employee_id", 'in', yearly_values.mapped('employee_id').ids)],
            groupby=["employee_id", "valid_as_of:year", "valid_as_of:month"],
            aggregates=["id:recordset"])

        mapped_payslips = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: self.env["hr.payslip"])))
        for emp, date_y, date_m, slip in paid_slips:
            mapped_payslips[emp][date_y.year][date_m.month] = slip

        mapped_qst_ema = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: self.env["l10n.ch.is.mutation"])))
        for emp, date_y, date_m, ema in qst_ema:
            # In the case of canton changes, naturalisations or C-permit, valid as of will be the last day of the month
            for e in ema:
                if e.reason == "withdrawalCanton":
                    qst_ema_real_date = e.valid_as_of + relativedelta(days=1)
                else:
                    qst_ema_real_date = e.valid_as_of
                mapped_qst_ema[emp][qst_ema_real_date.year][qst_ema_real_date.month] += e

        staff = []
        global_qst_institutions = self.env["l10n.ch.source.tax.institution"]

        for snapshot_y in yearly_values:
            snapshot = snapshot_y.monthly_value_ids.filtered(lambda y: y.month == month)
            tax_at_source_salaries = []
            current_payslips = mapped_payslips[snapshot.employee_id][snapshot.year][snapshot.month]
            if not current_payslips:
                continue
            current_payslip = current_payslips[-1]
            current_is_log_lines = current_payslips.mapped('l10n_ch_is_log_line_ids')
            if any(current_is_log_lines.mapped('source_tax_canton')):
                all_cantons = current_is_log_lines.filtered(lambda l: l.source_tax_canton).mapped('source_tax_canton')
                corrections_present = any(current_is_log_lines.mapped('is_correction'))

                # Ensure all cantons have a corresponding QST institution
                for canton in set(all_cantons):
                    if canton and not mapped_qst_institutions.get(canton):
                        raise ValidationError(_('Please define a Source-Tax institution with a valid DPI Number for Canton %(canton)s', canton=canton))

                # 1) Normal Classic Case, no corrections, no canton change only one TaxAtSource Salary
                if not corrections_present and len(set(all_cantons)) == 1:
                    year_sub = 1 if snapshot.month == 1 else 0
                    valid_source_tax_snapshot = snapshot

                    current_workplace = current_payslip.l10n_ch_location_unit_id
                    current_st_canton = all_cantons[0]
                    current_st_code = current_is_log_lines.mapped("is_code")[0]
                    current_st_municipality = valid_source_tax_snapshot.employee_meta_data.get('st-municipality', MISSING_VALUE)
                    current_st_type = valid_source_tax_snapshot.employee_meta_data.get('st-type', "TaxAtSourceCode")
                    current_qst_institution = mapped_qst_institutions.get(current_st_canton, MISSING_VALUE)

                    qst_salary = {
                        "institutionIDRef": swissdec_declaration.get_institution_id_ref(current_qst_institution),
                        "AdditionalParticulars": valid_source_tax_snapshot.additional_particular,
                        "CurrentMonth": [XSD_YMONTH, current_payslip.date_from.year, current_payslip.date_from.month, False],
                        "TaxAtSourceMunicipalityID": current_st_municipality,
                        "TaxAtSourceCanton": current_st_canton,
                    }

                    qst_current = {
                        "workplaceIDRef": swissdec_declaration.get_workplace_id_ref(current_workplace),
                        "WorkMunicipalityID": current_workplace.municipality or MISSING_VALUE,
                        "TaxAtSourceCategory": {
                            current_st_type: current_st_code
                        },
                        "Residence": valid_source_tax_snapshot.employee_meta_data.get("Residence", MISSING_VALUE),
                    }

                    self._fill_xml_scheme(qst_current, "GrantTaxAtSourceCode", XSD_SKIP_VALUE if valid_source_tax_snapshot.employee_meta_data.get('aci_approved', False) else False, False,)
                    self._fill_xml_scheme(qst_current, "TaxableEarning", current_is_log_lines.filtered(lambda l: l.code == "ISSALARY"), True, lambda_f=lambda lines: self._amount2str(sum(lines.mapped("amount"))))
                    self._fill_xml_scheme(qst_current, "AscertainedTaxableEarning", current_is_log_lines.filtered(lambda l: l.code == "ISDTSALARY"), True, lambda_f=lambda lines: self._amount2str(sum(lines.mapped("amount"))/ len(current_payslips)))
                    self._fill_xml_scheme(qst_current, "TaxAtSource", current_is_log_lines.filtered(lambda l: l.code == "IS"), True, lambda_f=lambda lines: self._amount2str(sum(lines.mapped("amount"))))

                    sporadic_benefits = sum(current_is_log_lines.filtered(lambda l: l.code == "ISDTSALARYAPERIODIC").mapped("amount"))
                    if sporadic_benefits:
                        qst_current["SporadicBenefits"] = self._amount2str(sporadic_benefits)

                    declaration_category = {}
                    relevant_ema = mapped_qst_ema[snapshot.employee_id][snapshot.year][snapshot.month].filtered(lambda ema: not ema.is_correction_id)
                    canton_change = False
                    for ema in relevant_ema:
                        ema_declaration_category, reason = IS_REASON_MAPPING[ema.reason]
                        # This EMA has to be declared in the appropriate QST institution
                        if reason == "cantonChange" and ema.reason == "withdrawalCanton":
                            canton_change = True
                            previous_canton = ema.qst_canton
                            previous_municipality = ema.qst_municipality
                            continue
                        declaration_category[ema_declaration_category] = declaration_category.get(ema_declaration_category, []) + [{"Reason": reason, "ValidAsOf": format_date(self.env, ema.valid_as_of, date_format='yyyy-MM-dd')}]

                    if declaration_category:
                        qst_current["DeclarationCategory"] = declaration_category

                    tax_at_source_salaries.append({
                        **qst_salary,
                        "Current": qst_current
                    })
                    global_qst_institutions += current_qst_institution
                    if canton_change:
                        previous_qst_institution = mapped_qst_institutions.get(previous_canton, MISSING_VALUE)
                        qst_salary_previous = {
                            "institutionIDRef": swissdec_declaration.get_institution_id_ref(previous_qst_institution),
                            "AdditionalParticulars": valid_source_tax_snapshot.additional_particular,
                            "CurrentMonth": [XSD_YMONTH, current_payslip.date_from.year, current_payslip.date_from.month, False],
                            "TaxAtSourceMunicipalityID": previous_municipality or MISSING_VALUE,
                            "TaxAtSourceCanton": previous_canton,
                        }

                        qst_current_previous = {
                            "workplaceIDRef": swissdec_declaration.get_workplace_id_ref(current_workplace),
                            "WorkMunicipalityID": current_workplace.municipality or MISSING_VALUE,
                            "TaxAtSourceCategory": {
                                current_st_type: current_st_code
                            },
                            "Residence": valid_source_tax_snapshot.employee_meta_data.get("Residence", MISSING_VALUE),
                            "TaxableEarning": "0.00",
                            "AscertainedTaxableEarning": "0.00",
                            "TaxAtSource": "0.00",
                        }
                        self._fill_xml_scheme(qst_current_previous, "GrantTaxAtSourceCode", XSD_SKIP_VALUE if snapshot.employee_meta_data.get('aci_approved', False) else False,False)

                        previous_declaration_category = {}
                        relevant_ema = mapped_qst_ema[snapshot.employee_id][snapshot.year][snapshot.month]
                        for ema in relevant_ema:
                            ema_declaration_category, reason = IS_REASON_MAPPING[ema.reason]
                            # This EMA was declared in the QST institution above
                            if reason == "cantonChange" and ema.reason == "entryCanton":
                                continue
                            previous_declaration_category[ema_declaration_category] = previous_declaration_category.get(ema_declaration_category, []) + [{"Reason": reason, "ValidAsOf": format_date(self.env, ema.valid_as_of, date_format='yyyy-MM-dd')}]
                        if previous_declaration_category:
                            qst_current_previous["DeclarationCategory"] = previous_declaration_category

                        tax_at_source_salaries.append({
                            **qst_salary_previous,
                            "Current": qst_current_previous
                        })
                        global_qst_institutions += previous_qst_institution


                # 2) Corrections Present without Canton Correction, 2 possible cases :
                elif corrections_present and len(set(all_cantons)) == 1:
                    # Case 1: After departure payment with ST Correction
                    if current_payslip.l10n_ch_after_departure_payment == "NK":
                        reference_payslip = current_is_log_lines.mapped('corrected_slip_id')[0]
                        valid_source_tax_snapshot = snapshot

                        current_st_canton = all_cantons[0]
                        current_st_municipality = valid_source_tax_snapshot.employee_meta_data.get('st-municipality', MISSING_VALUE)
                        current_qst_institution = mapped_qst_institutions.get(current_st_canton, MISSING_VALUE)

                        qst_salary = {
                            "institutionIDRef": swissdec_declaration.get_institution_id_ref(current_qst_institution),
                            "AdditionalParticulars": valid_source_tax_snapshot.additional_particular,
                            "CurrentMonth": [XSD_YMONTH, current_payslip.date_from.year,
                                             current_payslip.date_from.month, False],
                            "TaxAtSourceMunicipalityID": current_st_municipality,
                            "TaxAtSourceCanton": current_st_canton,
                        }

                        corrections = []
                        old_lines = current_is_log_lines.filtered(lambda l: l.correction_type == 'old')
                        new_lines = current_is_log_lines.filtered(lambda l: l.correction_type == 'new')
                        old = {
                            "TaxAtSourceCategory": {
                                swissdec_declaration._reverse_is_code_type(old_lines[0].is_code or "NON"): old_lines[0].is_code
                            }
                        }
                        new = {
                            "TaxAtSourceCategory": {
                                swissdec_declaration._reverse_is_code_type(new_lines[0].is_code): new_lines[0].is_code
                            }
                        }
                        for line in old_lines:
                            if line.code in QST_MAPPING:
                                old[QST_MAPPING[line.code]] = self._amount2str(line.amount)
                        for line in new_lines:
                            if line.code in QST_MAPPING:
                                new[QST_MAPPING[line.code]] = self._amount2str(line.amount)

                        corrections.append({
                            "Month": [XSD_YMONTH, reference_payslip.date_to.year, reference_payslip.date_to.month, False],
                            "Old": old,
                            "New": new
                        })

                        tax_at_source_salaries.append({
                            **qst_salary,
                            "Correction": corrections
                        })
                        global_qst_institutions += current_qst_institution

                    # Case 2: A correction either by the DPI or the ACI was performed
                    else:
                        valid_source_tax_snapshot = snapshot
                        current_workplace = current_payslip.l10n_ch_location_unit_id
                        current_correction = current_payslip.l10n_ch_is_correction
                        current_st_canton, current_st_code, current_st_municipality = current_payslip.l10n_ch_is_code.split('-')
                        current_st_type = swissdec_declaration._reverse_is_code_type(current_st_code)
                        current_qst_institution = mapped_qst_institutions.get(current_st_canton, MISSING_VALUE)

                        qst_salary = {
                            "institutionIDRef": swissdec_declaration.get_institution_id_ref(current_qst_institution),
                            "AdditionalParticulars": valid_source_tax_snapshot.additional_particular,
                            "CurrentMonth": [XSD_YMONTH, current_payslip.date_from.year,
                                             current_payslip.date_from.month, False],
                            "TaxAtSourceMunicipalityID": current_st_municipality,
                            "TaxAtSourceCanton": current_st_canton,
                        }

                        qst_current = {
                            "workplaceIDRef": swissdec_declaration.get_workplace_id_ref(current_workplace),
                            "WorkMunicipalityID": current_workplace.municipality or MISSING_VALUE,
                            "TaxAtSourceCategory": {
                                current_st_type: current_st_code
                            },
                            "Residence": valid_source_tax_snapshot.employee_meta_data.get("Residence", MISSING_VALUE),
                        }
                        self._fill_xml_scheme(qst_current, "GrantTaxAtSourceCode", XSD_SKIP_VALUE if snapshot.employee_meta_data.get('aci_approved', False) else False, False)
                        self._fill_xml_scheme(qst_current, "TaxableEarning",
                                             current_is_log_lines.filtered(lambda l: l.code == "ISSALARY" and not l.is_correction), True,
                                             lambda_f=lambda lines: self._amount2str(sum(lines.mapped("amount"))))
                        self._fill_xml_scheme(qst_current, "AscertainedTaxableEarning",
                                             current_is_log_lines.filtered(lambda l: l.code == "ISDTSALARY" and not l.is_correction), True,
                                             lambda_f=lambda lines: self._amount2str(sum(lines.mapped("amount"))))
                        self._fill_xml_scheme(qst_current, "TaxAtSource",
                                             current_is_log_lines.filtered(lambda l: l.code == "IS" and not l.is_correction), True,
                                             lambda_f=lambda lines: self._amount2str(sum(lines.mapped("amount"))))
                        self._fill_xml_scheme(qst_current, "SporadicBenefits",
                                             current_is_log_lines.filtered(lambda l: l.code == "ISDTSALARYAPERIODIC" and not l.is_correction),
                                             False, lambda_f=lambda lines: self._amount2str(sum(lines.mapped("amount"))))
                        corrections = []
                        correction_log_lines = current_is_log_lines.filtered(lambda l: l.corrected_slip_id)

                        if correction_log_lines:
                            corrected_slips_lines = correction_log_lines.grouped("corrected_slip_id")
                            if current_correction.correction_type == "dpi":
                                for c_slip in corrected_slips_lines:
                                    old_lines = corrected_slips_lines[c_slip].filtered(lambda l: l.correction_type == 'old')
                                    new_lines = corrected_slips_lines[c_slip].filtered(lambda l: l.correction_type == 'new')
                                    correction = dict()
                                    old = {
                                        "TaxAtSourceCategory": {
                                            swissdec_declaration._reverse_is_code_type(old_lines[0].is_code): old_lines[0].is_code or "NON"
                                        },
                                        "TaxableEarning": "0.00",
                                        "AscertainedTaxableEarning": "0.00",
                                        "TaxAtSource": "0.00",
                                    }
                                    for line in old_lines:
                                        if line.code in QST_MAPPING:
                                            old[QST_MAPPING[line.code]] = self._amount2str(line.amount)
                                    correction["Old"] = old
                                    new = {
                                        "TaxAtSourceCategory": {
                                            swissdec_declaration._reverse_is_code_type(new_lines[0].is_code): new_lines[0].is_code
                                        },
                                        "TaxableEarning": "0.00",
                                        "AscertainedTaxableEarning": "0.00",
                                        "TaxAtSource": "0.00",
                                        **swissdec_declaration.source_tax_ema_to_dict(current_correction.is_ema_ids)
                                    }
                                    for line in new_lines:
                                        if line.code in QST_MAPPING:
                                            new[QST_MAPPING[line.code]] = self._amount2str(line.amount)
                                    correction["New"] = new
                                    corrections.append({
                                        "Month": [XSD_YMONTH, c_slip.date_to.year, c_slip.date_to.month, False],
                                        **correction
                                    })
                                tax_at_source_salaries.append({
                                    **qst_salary,
                                    "Current": qst_current,
                                    "Correction": corrections
                                })
                            elif current_correction.correction_type == "aci":
                                for c_slip in corrected_slips_lines:
                                    all_lines = corrected_slips_lines[c_slip].filtered(lambda l: l.correction_type)
                                    new = {}
                                    for line in all_lines:
                                        if line.code in ["IS", "ISSALARY"]:
                                            new[QST_MAPPING[line.code]] = self._amount2str(float(new.get(QST_MAPPING[line.code], 0)) + line.amount)

                                    corrections.append({
                                        "Month": [XSD_YMONTH, c_slip.date_to.year, c_slip.date_to.month, False],
                                        **new
                                    })
                                qst_current.update(swissdec_declaration.source_tax_ema_to_dict(current_correction.is_ema_ids))
                                tax_at_source_salaries.append({
                                    **qst_salary,
                                    "Current": qst_current,
                                    "CorrectionConfirmed": corrections
                                })
                            global_qst_institutions += current_qst_institution

                # 3) Corrections Present WITH canton correction
                elif corrections_present and len(set(all_cantons)) == 2:
                    new_canton = current_payslip.l10n_ch_is_code.split('-')[0]
                    all_canton_set = set(all_cantons)
                    all_canton_set.remove(new_canton)
                    old_canton = all_canton_set.pop()
                    current_correction = current_payslip.l10n_ch_is_correction

                    old_qst_institution = mapped_qst_institutions.get(old_canton, MISSING_VALUE)
                    new_qst_institution = mapped_qst_institutions.get(new_canton, MISSING_VALUE)

                    ##################################################
                    # 2) Split lines into three groups:
                    #    - Non-correction lines in the new canton ("current" for new)
                    #    - Correction lines for the old canton
                    #    - Correction lines for the new canton
                    ##################################################

                    all_lines = current_is_log_lines
                    non_correction_lines_new_canton = all_lines.filtered(
                        lambda l: not l.corrected_slip_id and l.source_tax_canton == new_canton)
                    correction_lines_old_canton = all_lines.filtered(
                        lambda l: l.corrected_slip_id and l.source_tax_canton == old_canton)
                    correction_lines_new_canton = all_lines.filtered(
                        lambda l: l.corrected_slip_id and l.source_tax_canton == new_canton)

                    ##################################################
                    # 3) Build the OLD canton dictionary
                    #    "Current" = 0
                    #    "Correction" = array of items, one per corrected slip
                    #       "Old" = sum of old lines
                    #       "New" = 0.00
                    ##################################################
                    first_line = non_correction_lines_new_canton[0]
                    st_type = swissdec_declaration._reverse_is_code_type(first_line.is_code)

                    old_canton_dict = {
                        "institutionIDRef": swissdec_declaration.get_institution_id_ref(old_qst_institution),
                        "AdditionalParticulars": snapshot.additional_particular,
                        "CurrentMonth": [XSD_YMONTH, current_payslip.date_from.year, current_payslip.date_from.month,
                                         False],
                        "TaxAtSourceMunicipalityID": correction_lines_old_canton[-1].source_tax_municipality,
                        "TaxAtSourceCanton": old_canton,
                        "Current": {
                            "workplaceIDRef": swissdec_declaration.get_workplace_id_ref(
                                current_payslip.l10n_ch_location_unit_id),
                            "WorkMunicipalityID": current_payslip.l10n_ch_location_unit_id.municipality or MISSING_VALUE,
                            "TaxAtSourceCategory": {st_type: first_line.is_code},
                            "Residence": snapshot.employee_meta_data.get("Residence", MISSING_VALUE),
                            "TaxableEarning": "0.00",
                            "AscertainedTaxableEarning": "0.00",
                            "TaxAtSource": "0.00",
                            **swissdec_declaration.source_tax_ema_to_dict(current_correction.is_ema_ids.filtered(lambda c: c.qst_canton == old_canton))
                        }
                    }

                    correction_by_slip_old = correction_lines_old_canton.grouped("corrected_slip_id")
                    old_corrections = []

                    for c_slip, lines_for_this_slip in correction_by_slip_old.items():
                        first_line = lines_for_this_slip[0]
                        st_type = swissdec_declaration._reverse_is_code_type(first_line.is_code)

                        old_part = {
                            "TaxAtSourceCategory": {st_type: first_line.is_code},  # we might fill or keep empty, up to you
                            "TaxableEarning": "0.00",
                            "AscertainedTaxableEarning": "0.00",
                            "TaxAtSource": "0.00",
                        }

                        old_lines_here = lines_for_this_slip.filtered(lambda l: l.correction_type == "old")
                        for l in old_lines_here:
                            if l.code in QST_MAPPING:
                                mapped_key = QST_MAPPING[l.code]  # e.g. "TaxableEarning", "TaxAtSource", etc.
                                old_amount = float(old_part.get(mapped_key, 0.0))
                                old_part[mapped_key] = self._amount2str(old_amount + l.amount)

                        new_part = {
                            "TaxAtSourceCategory": {st_type: first_line.is_code},
                            "TaxableEarning": "0.00",
                            "AscertainedTaxableEarning": "0.00",
                            "TaxAtSource": "0.00",
                        }

                        old_corrections.append({
                            "Month": [XSD_YMONTH, c_slip.date_to.year, c_slip.date_to.month, False],
                            "Old": old_part,
                            "New": new_part
                        })

                    if old_corrections:
                        old_canton_dict["Correction"] = old_corrections

                    ##################################################
                    # 4) Build the NEW canton dictionary
                    #    "Current" = sum of any non-correction lines for the new canton
                    #    "Correction" = array of items, one per corrected slip
                    #       "Old" = 0.00
                    #       "New" = sum of lines from that slip
                    ##################################################

                    new_canton_dict = {
                        "institutionIDRef": swissdec_declaration.get_institution_id_ref(new_qst_institution),
                        "AdditionalParticulars": snapshot.additional_particular,
                        "CurrentMonth": [XSD_YMONTH, current_payslip.date_from.year, current_payslip.date_from.month,
                                         False],
                        "TaxAtSourceMunicipalityID": non_correction_lines_new_canton[-1].source_tax_municipality,
                        "TaxAtSourceCanton": new_canton,
                    }

                    if non_correction_lines_new_canton:
                        first_line = non_correction_lines_new_canton[0]
                        st_type = swissdec_declaration._reverse_is_code_type(first_line.is_code)
                        current_block = {
                            "workplaceIDRef": swissdec_declaration.get_workplace_id_ref(
                                current_payslip.l10n_ch_location_unit_id),
                            "WorkMunicipalityID": current_payslip.l10n_ch_location_unit_id.municipality or MISSING_VALUE,
                            "TaxAtSourceCategory": {st_type: first_line.is_code},
                            "Residence": snapshot.employee_meta_data.get("Residence", MISSING_VALUE),
                            **swissdec_declaration.source_tax_ema_to_dict(current_correction.is_ema_ids.filtered(lambda c: c.qst_canton == new_canton))
                        }
                        self._fill_xml_scheme(
                            current_block, "TaxableEarning",
                            non_correction_lines_new_canton.filtered(lambda l: l.code == "ISSALARY"),
                            True,
                            lambda_f=lambda lines: self._amount2str(sum(lines.mapped("amount")))
                        )
                        self._fill_xml_scheme(
                            current_block, "AscertainedTaxableEarning",
                            non_correction_lines_new_canton.filtered(lambda l: l.code == "ISDTSALARY"),
                            True,
                            lambda_f=lambda lines: self._amount2str(sum(lines.mapped("amount")))
                        )
                        self._fill_xml_scheme(
                            current_block, "TaxAtSource",
                            non_correction_lines_new_canton.filtered(lambda l: l.code == "IS"),
                            True,
                            lambda_f=lambda lines: self._amount2str(sum(lines.mapped("amount")))
                        )
                        self._fill_xml_scheme(
                            current_block, "SporadicBenefits",
                            non_correction_lines_new_canton.filtered(lambda l: l.code == "ISDTSALARYAPERIODIC"),
                            False,
                            lambda_f=lambda lines: self._amount2str(sum(lines.mapped("amount")))
                        )

                        new_canton_dict["Current"] = current_block

                    correction_by_slip_new = correction_lines_new_canton.grouped("corrected_slip_id")
                    new_corrections = []

                    for c_slip, lines_for_this_slip in correction_by_slip_new.items():
                        first_line = lines_for_this_slip[0]
                        st_type = swissdec_declaration._reverse_is_code_type(first_line.is_code)
                        # "Old" portion is forced to 0 for the new canton
                        old_part = {
                            "TaxAtSourceCategory": {st_type: first_line.is_code},
                            "TaxableEarning": "0.00",
                            "AscertainedTaxableEarning": "0.00",
                            "TaxAtSource": "0.00",
                        }
                        # "New" portion is the sum of correction lines whose correction_type == 'new'
                        new_part = {
                            "TaxAtSourceCategory": {st_type: first_line.is_code},
                            "TaxableEarning": "0.00",
                            "AscertainedTaxableEarning": "0.00",
                            "TaxAtSource": "0.00",
                        }
                        new_lines_here = lines_for_this_slip.filtered(lambda l: l.correction_type == "new")
                        for l in new_lines_here:
                            if l.code in QST_MAPPING:
                                mapped_key = QST_MAPPING[l.code]
                                new_amount = float(new_part.get(mapped_key, 0.0))
                                new_part[mapped_key] = self._amount2str(new_amount + l.amount)

                        new_corrections.append({
                            "Month": [XSD_YMONTH, c_slip.date_to.year, c_slip.date_to.month, False],
                            "Old": old_part,
                            "New": new_part
                        })

                    if new_corrections:
                        new_canton_dict["Correction"] = new_corrections

                    tax_at_source_salaries.append(old_canton_dict)
                    tax_at_source_salaries.append(new_canton_dict)

                    global_qst_institutions += old_qst_institution
                    global_qst_institutions += new_qst_institution

            salaries = {}
            if snapshot.person:
                if tax_at_source_salaries:
                    salaries["TaxAtSourceSalaries"] = {
                        "TaxAtSourceSalary": tax_at_source_salaries
                    }

                if salaries:
                    staff.append({
                        **snapshot.person,
                        **salaries
                    })
        if staff:
            staff_declaration = {
                "Staff": {
                    "Person": staff
                }
            }
            institutions_to_process = list(set(global_qst_institutions))

            declaration = {
                **swissdec_declaration.get_company_description(company_id),
                **staff_declaration,
                **swissdec_declaration.get_institutions(institutions_to_process),
                "SalaryCounters": swissdec_declaration.get_salary_tag_counter(staff_declaration),
                "SalaryTotals": swissdec_declaration.get_salary_totals(staff, CurrentMonth=[XSD_YMONTH, year, month, False], source_tax_commission_rates=source_tax_commission)
            }
            allowed_institutions = {
                "QST": set(global_qst_institutions.ids),
            }

        else:
            declaration = {}
            allowed_institutions = {}

        return declaration, allowed_institutions

    def _get_monthly_statistic(self, year, month, company_id):
        swissdec_declaration = SwissdecDeclaration()
        yearly_values = self.env["l10n.ch.employee.yearly.values"].search([("year", '=', year), ('employee_id.company_id', '=', company_id.id)])
        staff = []
        BFS = []

        for snapshot_y in yearly_values:
            snapshot = snapshot_y.monthly_value_ids.filtered(lambda y: y.month == month)
            salaries = {}
            if snapshot.person:
                if snapshot.monthly_statistics:
                    salaries["StatisticSalaries"] = snapshot.monthly_statistics.get("StatisticSalaries")
                    BFS = [SwissdecInstitution("BFS", pay_agreement=company_id.l10n_ch_statistics_convention, payroll_unit=company_id.l10n_ch_statistics_payroll_unit)]
                    staff.append({
                        **snapshot.person,
                        **salaries
                    })
        if staff:
            staff_declaration = {
                "Staff": {
                    "Person": staff
                }
            }
            institutions_to_process = BFS
            declaration = {
                **swissdec_declaration.get_company_description(company_id),
                **staff_declaration,
                **swissdec_declaration.get_institutions(institutions_to_process),
                "SalaryCounters": swissdec_declaration.get_salary_tag_counter(staff_declaration),
                "SalaryTotals": swissdec_declaration.get_salary_totals(staff, CurrentMonth=[XSD_YMONTH, year, month, False])
            }
            allowed_institutions = {
                "BFS": bool(BFS)
            }

        else:
            declaration = {}
            allowed_institutions = {}

        return declaration, allowed_institutions

    def _get_monthly_ema(self, year, month, company_id):
        swissdec_declaration = SwissdecDeclaration()

        paid_slips = self.env["hr.payslip"]._read_group(
            domain=[("company_id", '=', company_id.id), ("state", "in", ["paid", "done"]), ('struct_id.code', '=', 'CHMONTHLYELM')],
            groupby=["employee_id", "date_to:year", "date_to:month"],
            aggregates=["id:recordset"])

        mapped_payslips = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: self.env["hr.payslip"])))
        for emp, date_y, date_m, slip in paid_slips:
            mapped_payslips[emp][date_y.year][date_m.month] = slip


        mapped_contracts = dict(self.env["hr.contract"]._read_group(domain=[
            ('state', 'in', ['open', 'close']),
        ], groupby=["employee_id"],
            aggregates=["id:recordset"]
        ))
        yearly_values = self.env["l10n.ch.employee.yearly.values"].search([("year", '=', year), ('employee_id.company_id', '=', company_id.id)])
        mapped_lpp_mutations = self.env["l10n.ch.lpp.mutation"]._read_group(domain=[("employee_id", 'in', yearly_values.employee_id.ids)], groupby=["employee_id", "valid_as_of:year", "valid_as_of:month"], aggregates=["id:recordset"])
        mapped_mutations = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: self.env["l10n.ch.lpp.mutation"])))

        global_avs_institutions = self.env["l10n.ch.social.insurance"]
        global_caf_institutions = self.env["l10n.ch.compensation.fund"]
        global_lpp_institutions = self.env["l10n.ch.lpp.insurance"]

        for employee_id, date_y, date_m, ema in mapped_lpp_mutations:
            mapped_mutations[employee_id][date_y.year][date_m.month] += ema

        staff = []
        first_day_of_month = datetime.date(year, month, 1)
        last_day_of_month = first_day_of_month + relativedelta(months=1, days=-1)

        for snapshot_y in yearly_values:
            snapshot = snapshot_y.monthly_value_ids.filtered(lambda s: s.month == month)
            snapshot_contracts = mapped_contracts.get(snapshot.employee_id, self.env['hr.contract']).filtered(lambda c: (c.date_start <= last_day_of_month and (c.date_end >= first_day_of_month if c.date_end else True)))
            ema_values = dict()
            avs_ahv_salaries = []
            fak_caf_salaries = []
            bvg_lpp_salaries = []

            year_sub = 1 if snapshot.month == 1 else 0
            previous_payslip = mapped_payslips[snapshot.employee_id][snapshot.year - year_sub][(snapshot.month - 2) % 12 + 1]
            current_payslip = mapped_payslips[snapshot.employee_id][snapshot.year][snapshot.month]
            agricole_company = company_id.l10n_ch_agricole_company

            end_of_month = datetime.date(snapshot.year, snapshot.month, 26)
            for c in snapshot_contracts:
                contract_start_this_month = c.date_start.month == snapshot.month and c.date_start.year == snapshot.year
                contract_end_this_month = c.date_end and c.date_end.month == snapshot.month and c.date_end.year == snapshot.year
                caf_canton_change = previous_payslip.contract_id == current_payslip.contract_id and previous_payslip.contract_id == c and previous_payslip.l10n_ch_location_unit_id.canton != current_payslip.l10n_ch_location_unit_id.canton

                is_18th_anniversary_this_contract = False
                birthdate = snapshot.employee_id.birthday
                if not birthdate:
                    continue
                eighteenth_birthday = birthdate.replace(year=birthdate.year + 18)
                is_18th_anniversary = (eighteenth_birthday.year == year and eighteenth_birthday.month == month)

                # Check if the 18th birthday is within the contract dates
                if is_18th_anniversary:
                    is_18th_anniversary_this_contract = (
                            c.date_start <= eighteenth_birthday and
                            (eighteenth_birthday <= c.date_end if c.date_end else True)
                    )

                lpp_entry_this_month = c.l10n_ch_lpp_insurance_id and c.l10n_ch_lpp_entry_valid_as_of and c.l10n_ch_lpp_entry_valid_as_of.month == snapshot.month and c.l10n_ch_lpp_entry_valid_as_of.year == snapshot.year
                lpp_withdrawal_this_month = c.l10n_ch_lpp_insurance_id and c.l10n_ch_lpp_withdrawal_valid_as_of and c.l10n_ch_lpp_withdrawal_valid_as_of.month == snapshot.month and c.l10n_ch_lpp_withdrawal_valid_as_of.year == snapshot.year


                if contract_start_this_month and not c.l10n_ch_avs_status == "youth":
                    avs_ahv_salaries.append(swissdec_declaration.create_ahv_avs_ema(
                        institution_id=c.l10n_ch_social_insurance_id,
                        declaration_category="Entry",
                        valid_as_of=format_date(self.env, c.date_start, date_format='yyyy-MM-dd'),
                        month=snapshot.month,
                        year=snapshot.year,
                        acc_from=format_date(self.env, c.date_start, date_format='yyyy-MM-dd'),
                        acc_until=format_date(self.env, max(c.date_start, end_of_month), date_format='yyyy-MM-dd'),
                        ceo_rel=snapshot.employee_id.l10n_ch_relationship_ceo if agricole_company else False
                    ))
                    global_avs_institutions += c.l10n_ch_social_insurance_id
                if is_18th_anniversary_this_contract:
                    avs_ahv_salaries.append(swissdec_declaration.create_ahv_avs_ema(
                        institution_id=c.l10n_ch_social_insurance_id,
                        declaration_category="Entry",
                        valid_as_of=format_date(self.env, eighteenth_birthday, date_format='yyyy-MM-dd'),
                        month=snapshot.month,
                        year=snapshot.year,
                        acc_from=format_date(self.env, c.date_start, date_format='yyyy-MM-dd'),
                        acc_until=format_date(self.env, max(c.date_start, end_of_month), date_format='yyyy-MM-dd'),
                        ceo_rel=snapshot.employee_id.l10n_ch_relationship_ceo if agricole_company else False
                    ))
                    global_avs_institutions += c.l10n_ch_social_insurance_id


                if contract_end_this_month and not c.l10n_ch_avs_status == "youth":
                    avs_ahv_salaries.append(swissdec_declaration.create_ahv_avs_ema(
                        institution_id=c.l10n_ch_social_insurance_id,
                        declaration_category="Withdrawal",
                        valid_as_of=format_date(self.env, c.date_end, date_format='yyyy-MM-dd'),
                        month=snapshot.month,
                        year=snapshot.year,
                        acc_from=format_date(self.env, c.date_start, date_format='yyyy-MM-dd'),
                        acc_until=format_date(self.env, max(c.date_start, end_of_month), date_format='yyyy-MM-dd'),
                        ceo_rel=snapshot.employee_id.l10n_ch_relationship_ceo if agricole_company else False
                    ))
                    global_avs_institutions += c.l10n_ch_social_insurance_id

                if contract_start_this_month and not c.l10n_ch_avs_status == "youth":
                    fak_caf_salaries.append(swissdec_declaration.create_fak_caf_ema(
                        institution_id=c.l10n_ch_compensation_fund_id,
                        canton=c.l10n_ch_location_unit_id.canton,
                        declaration_category="Entry",
                        valid_as_of=format_date(self.env, c.date_start, date_format='yyyy-MM-dd'),
                        reason="entryCompany",
                        period_from=format_date(self.env, c.date_start, date_format='yyyy-MM-dd'),
                        period_until=format_date(self.env, max(c.date_start, end_of_month), date_format='yyyy-MM-dd'),
                    ))
                    global_caf_institutions += c.l10n_ch_compensation_fund_id

                if is_18th_anniversary_this_contract:
                    fak_caf_salaries.append(swissdec_declaration.create_fak_caf_ema(
                        institution_id=c.l10n_ch_compensation_fund_id,
                        canton=c.l10n_ch_location_unit_id.canton,
                        declaration_category="Entry",
                        valid_as_of=format_date(self.env, eighteenth_birthday, date_format='yyyy-MM-dd'),
                        reason="entryCompany",
                        period_from=format_date(self.env, c.date_start, date_format='yyyy-MM-dd'),
                        period_until=format_date(self.env, max(c.date_start, end_of_month), date_format='yyyy-MM-dd'),
                    ))
                    global_caf_institutions += c.l10n_ch_compensation_fund_id

                if contract_end_this_month and not c.l10n_ch_avs_status == "youth":
                    fak_caf_salaries.append(swissdec_declaration.create_fak_caf_ema(
                        institution_id=c.l10n_ch_compensation_fund_id,
                        canton=c.l10n_ch_location_unit_id.canton,
                        declaration_category="Withdrawal",
                        valid_as_of=format_date(self.env, c.date_end, date_format='yyyy-MM-dd'),
                        reason="withdrawalCompany",
                        period_from=format_date(self.env, c.date_start, date_format='yyyy-MM-dd'),
                        period_until=format_date(self.env, max(c.date_start, end_of_month), date_format='yyyy-MM-dd'),
                    ))
                    global_caf_institutions += c.l10n_ch_compensation_fund_id

                if caf_canton_change and not c.l10n_ch_avs_status == "youth":
                    fak_caf_salaries.append(swissdec_declaration.create_fak_caf_ema(
                        institution_id=previous_payslip.l10n_ch_compensation_fund_id,
                        canton=current_payslip.l10n_ch_location_unit_id.canton,
                        declaration_category="Withdrawal",
                        valid_as_of=format_date(self.env, datetime.date(snapshot.year, snapshot.month, 1) + relativedelta(days=-1), date_format='yyyy-MM-dd'),
                        reason="cantonChange",
                        period_from=format_date(self.env, c.date_start, date_format='yyyy-MM-dd'),
                        period_until=format_date(self.env, max(c.date_start, end_of_month), date_format='yyyy-MM-dd'),
                    ))
                    global_caf_institutions += previous_payslip.l10n_ch_compensation_fund_id

                    fak_caf_salaries.append(swissdec_declaration.create_fak_caf_ema(
                        institution_id=current_payslip.l10n_ch_compensation_fund_id,
                        canton=current_payslip.l10n_ch_location_unit_id.canton,
                        declaration_category="Entry",
                        valid_as_of=format_date(self.env, datetime.date(snapshot.year, snapshot.month, 1), date_format='yyyy-MM-dd'),
                        reason="cantonChange",
                        period_from=format_date(self.env, c.date_start, date_format='yyyy-MM-dd'),
                        period_until=format_date(self.env, max(c.date_start, end_of_month), date_format='yyyy-MM-dd'),
                    ))
                    global_caf_institutions += current_payslip.l10n_ch_compensation_fund_id

                lpp_declarations = {
                    "Entry": [],
                    "Withdrawal": [],
                    "Mutation": []
                }
                if lpp_entry_this_month and not c.l10n_ch_avs_status == "youth":
                    lpp_declarations["Entry"].append(
                        {"ValidAsOf": format_date(self.env, c.l10n_ch_lpp_entry_valid_as_of, date_format='yyyy-MM-dd'), "Reason":  c.l10n_ch_lpp_entry_reason}
                    )
                if lpp_withdrawal_this_month and not c.l10n_ch_avs_status == "youth":
                    lpp_declarations["Withdrawal"].append(
                        {"ValidAsOf": format_date(self.env, c.l10n_ch_lpp_withdrawal_valid_as_of, date_format='yyyy-MM-dd'), "Reason": c.l10n_ch_lpp_withdrawal_reason}
                    )
                if (not c.l10n_ch_lpp_not_insured) and c.l10n_ch_lpp_insurance_id and not c.l10n_ch_avs_status == "youth":
                    for mutation in mapped_mutations[snapshot.employee_id][snapshot.year][snapshot.month]:
                        lpp_declarations["Mutation"].append(
                            {"ValidAsOf": format_date(self.env, mutation.valid_as_of, date_format='yyyy-MM-dd'), "Reason": mutation.reason}
                        )

                if any(lpp_declarations.values()):
                    bvg_lpp_salaries.append(swissdec_declaration.create_bvg_lpp_ema(
                        institution_id=c.l10n_ch_lpp_insurance_id,
                        declarations=lpp_declarations,
                        codes=c.l10n_ch_lpp_solutions.mapped('code') if c.l10n_ch_lpp_solutions else False,
                        bvg_lpp_annual_basis=snapshot.bvg_lpp_annual_basis
                    ))
                    global_lpp_institutions += c.l10n_ch_lpp_insurance_id



            if avs_ahv_salaries:
                ema_values.update({
                    "AHV-AVS-Salaries": {
                        "AHV-AVS-Salary": avs_ahv_salaries
                    }
                })

            if fak_caf_salaries:
                ema_values.update({
                    "FAK-CAF-Salaries": {
                        "FAK-CAF-Salary": fak_caf_salaries
                }})

            if bvg_lpp_salaries:
                ema_values.update({
                    "BVG-LPP-Salaries": {
                        "BVG-LPP-Salary": bvg_lpp_salaries
                    }
                })
            if ema_values and snapshot.person:
                staff.append({
                    **snapshot.person,
                    **ema_values
                })

        if staff:
            staff_declaration = {
                "Staff": {
                    "Person": staff
                }
            }
            institutions_to_process = list(set(global_avs_institutions)) + list(set(global_caf_institutions)) + list(set(global_lpp_institutions))
            declaration = {
                **swissdec_declaration.get_company_description(company_id),
                **staff_declaration,
                **swissdec_declaration.get_institutions(institutions_to_process, general_validasof=format_date(self.env, datetime.date(year, int(month), 1), date_format='yyyy-MM-dd')),
                "SalaryCounters": swissdec_declaration.get_salary_tag_counter(staff_declaration),
                "SalaryTotals": swissdec_declaration.get_salary_totals(staff)
            }

            allowed_institutions = {
                "AVS": set(global_avs_institutions.ids),
                "CAF": set(global_caf_institutions.ids),
                "LPP": set(global_lpp_institutions.ids),
            }
        else:
            declaration = {}
            allowed_institutions = {}

        return declaration, allowed_institutions

    def _generate_certificate_uuid(self):
        return uuid.uuid4().hex

    def _create_wage_statement(self, current_certificate, period_from, period_to, relevant_tax_slips, line_values, last_monthly_value, rules_grouped_by_certificate_section, year_delta, rectificate_original_id=None, rectificate_original_date=None):
        if last_monthly_value.person:
            last_valid_activity_rate = float(last_monthly_value.person.get("Work", {}).get("WorkingTime", {}).get("Steady", {}).get("ActivityRate", "100"))
        else:
            last_valid_activity_rate = 100

        salary_certificate = {
            "DocID": self._generate_certificate_uuid(),
            "Period": {
                "from": format_date(self.env, period_from,
                                    date_format='yyyy-MM-dd'),
                "until": format_date(self.env, period_to, date_format='yyyy-MM-dd')
            },
            "GrossIncome": "0.00",
            "NetIncome": "0.00"
        }
        any_amount = False
        for section in rules_grouped_by_certificate_section:
            if section in CERTIFICATE_RULE_MAPPING:
                key_path = CERTIFICATE_RULE_MAPPING[section]
                # Lump sum Type -> We need to explicit what kind of wage type it is
                if section in ['2.3', '3', '4', '7', '13.1.2', '13.2.3']:
                    payslip_lines = relevant_tax_slips.filtered(
                        lambda p: p.l10n_ch_after_departure_payment if year_delta else True).line_ids.filtered(
                        lambda pl: pl.salary_rule_id.l10n_ch_salary_certificate == section).sorted(
                        lambda pl: pl.salary_rule_id.l10n_ch_code)
                    text = ', '.join(sorted([w_t for w_t in set(payslip_lines.mapped('name'))]))
                    sum_value = sum(payslip_lines.mapped('total'))
                    if sum_value:
                        salary_certificate[key_path] = salary_certificate.get(key_path, []) + [{
                            "Text": text,
                            "Sum": self._amount2str(sum_value)
                        }]  # Salary Amount Type
                else:
                    sum_value = sum([line_values[mapped_rule.code][p.id]['total'] for p in relevant_tax_slips.filtered(
                        lambda p: p.l10n_ch_after_departure_payment if year_delta else True) for mapped_rule in
                                     rules_grouped_by_certificate_section[section]])
                    if sum_value:
                        if section in ["9", "12"]:
                            salary_certificate[key_path] = self._amount2str(-sum_value)
                        else:
                            salary_certificate[key_path] = self._amount2str(abs(sum_value))
                if int(section.split(".")[0]) < 8 and sum_value:
                    salary_certificate["GrossIncome"] = self._amount2str(
                        float(salary_certificate.get("GrossIncome", "0.00")) + sum_value)
                if sum_value:
                    any_amount = True

        salary_certificate["NetIncome"] = self._amount2str(
            float(salary_certificate.get("GrossIncome", "0.00")) - float(
                salary_certificate.get("AHV-ALV-NBUV-AVS-AC-AANP-Contribution", "0.00")) - float(
                salary_certificate.get("BVG-LPP-Contribution/Purchase", "0.00")) - float(
                salary_certificate.get("BVG-LPP-Contribution/Regular", "0.00")))

        # 14 - 15 : Standard Remarks
        if current_certificate:
            standard_remarks = dict()
            if last_valid_activity_rate != 100:
                standard_remarks["ActivityRate"] = self._amount2str(last_valid_activity_rate)
            if current_certificate.l10n_ch_cs_other_fringe_benefits:
                salary_certificate['OtherFringeBenefits'] = current_certificate.l10n_ch_cs_other_fringe_benefits
            if current_certificate.l10n_ch_cs_free_transport:
                salary_certificate['FreeTransport'] = XSD_SKIP_VALUE
            if current_certificate.l10n_ch_cs_free_meals:
                salary_certificate['CanteenLunchCheck'] = XSD_SKIP_VALUE

            if current_certificate.l10n_ch_source_tax_settlement_letter:
                standard_remarks["TaxAtSourcePeriodForObjection"] = XSD_SKIP_VALUE
            if current_certificate.l10n_ch_cs_additional_text:
                salary_certificate["Remark"] = current_certificate.l10n_ch_cs_additional_text

            if current_certificate.l10n_ch_cs_expense_policy:
                if current_certificate.l10n_ch_cs_expense_policy == "approved":
                    salary_certificate["ChargesRule"] = {
                        "WithRegulation": {
                            "Allowed": format_date(self.env,
                                                   current_certificate.l10n_ch_cs_expense_policy_approved_date,
                                                   date_format='yyyy-MM-dd'),
                            "Canton": current_certificate.l10n_ch_cs_expense_policy_approved_canton
                        }
                    }
                    if CERTIFICATE_RULE_MAPPING["13.1.1"] in salary_certificate:
                        del salary_certificate[CERTIFICATE_RULE_MAPPING["13.1.1"]]
                elif current_certificate.l10n_ch_cs_expense_policy == "rz52":
                    salary_certificate["ChargesRule"] = {
                        "Guidance": XSD_SKIP_VALUE
                    }
                    if CERTIFICATE_RULE_MAPPING["13.1.1"] in salary_certificate:
                        del salary_certificate[CERTIFICATE_RULE_MAPPING["13.1.1"]]
            if current_certificate.l10n_ch_child_allowance_indirect:
                standard_remarks["ChildAllowancePerAHV-AVS"] = XSD_SKIP_VALUE
            if current_certificate.l10n_ch_relocation_costs:
                standard_remarks["RelocationCosts"] = self._amount2str(current_certificate.l10n_ch_relocation_costs)

            if current_certificate.l10n_ch_cs_employee_parti_fair_market_value:
                standard_remarks["StaffShareMarketValue"] = {
                    "Allowed": format_date(self.env,
                                           current_certificate.l10n_ch_cs_employee_parti_fair_market_value_date,
                                           date_format='yyyy-MM-dd'),
                    "Canton": current_certificate.l10n_ch_cs_employee_parti_fair_market_value_canton
                }

            if current_certificate.l10n_ch_cs_employee_participation_taxable_income:
                staff_shares = dict()
                if current_certificate.l10n_ch_cs_employee_participation_taxable_income_locked:
                    staff_shares["BlockedOptions"] = XSD_SKIP_VALUE
                if current_certificate.l10n_ch_cs_employee_participation_taxable_income_unlisted:
                    staff_shares["UnquotedOptions"] = XSD_SKIP_VALUE
                if current_certificate.l10n_ch_cs_employee_participation_taxable_income_reversional:
                    staff_shares["DeferredBenefitsStaffShares"] = XSD_SKIP_VALUE
                if current_certificate.l10n_ch_cs_employee_participation_taxable_income_virtual:
                    staff_shares["FictitousStaffShare"] = XSD_SKIP_VALUE
                if staff_shares:
                    standard_remarks["StaffShareWithoutTaxableIncome"] = staff_shares
            if current_certificate.l10n_ch_cs_car_policy == "empPart":
                standard_remarks["MinimalEmployeeCarPartPercentage"] = XSD_SKIP_VALUE
            elif current_certificate.l10n_ch_cs_car_policy == "toClarify":
                standard_remarks["CompanyCarClarify"] = XSD_SKIP_VALUE
            if current_certificate.l10n_ch_source_tax_settlement_letter:
                standard_remarks["TaxAtSourcePeriodForObjection"] = XSD_SKIP_VALUE
            if current_certificate.l10n_ch_cs_expense_expatriate_ruling_approved:
                standard_remarks["ExpatriateRuling"] = {
                    "Allowed": format_date(self.env,
                                           current_certificate.l10n_ch_cs_expense_expatriate_ruling_approved_date,
                                           date_format='yyyy-MM-dd'),
                    "Canton": current_certificate.l10n_ch_cs_expense_expatriate_ruling_approved_canton
                }
            if current_certificate.l10n_ch_provision_salary:
                salary_provision = {
                    "Lastname": current_certificate.l10n_ch_provision_salary_last_name,
                    "Firstname": current_certificate.l10n_ch_provision_salary_first_name,
                }

                salary_provision_address = {
                    "ZIP-Code": current_certificate.l10n_ch_provision_salary_zip,
                    "City": current_certificate.l10n_ch_provision_salary_city
                }
                if current_certificate.l10n_ch_provision_salary_street:
                    salary_provision_address["Street"] = current_certificate.l10n_ch_provision_salary_street
                if current_certificate.l10n_ch_provision_salary_country:
                    salary_provision_address[
                        "Country"] = current_certificate.l10n_ch_provision_salary_country.name.upper()
                salary_provision["Address"] = salary_provision_address
                standard_remarks["ContinuedProvisionOfSalary"] = salary_provision
            if rectificate_original_id and rectificate_original_date:
                standard_remarks["Rectificate"] = {
                    "OriginalDate": format_date(self.env, rectificate_original_date, date_format='yyyy-MM-dd'),
                    "OriginalDocID": rectificate_original_id
                }

            if standard_remarks and current_certificate.l10n_ch_certificate_type != 'TaxAnnuity':
                salary_certificate["StandardRemark"] = standard_remarks

        if any_amount:
            return salary_certificate
        else:
            return False

    def _create_pension_statement(self, current_certificate, period_from, period_to, relevant_tax_slips, line_values, last_monthly_value, rules_grouped_by_certificate_section, year_delta, rectificate_original_id=None, rectificate_original_date=None):
        salary_certificate = {
            "DocID": self._generate_certificate_uuid(),
            "Period": {
                "from": format_date(self.env, period_from,
                                    date_format='yyyy-MM-dd'),
                "until": format_date(self.env, period_to, date_format='yyyy-MM-dd')
            },
            "GrossIncome": "0.00",
            "NetIncome": "0.00"
        }
        any_amount = False
        for section in rules_grouped_by_certificate_section:
            if section in ANNUITY_RULE_MAPPING:
                key_path = ANNUITY_RULE_MAPPING[section]
                # Lump sum Type -> We need to explicit what kind of wage type it is
                if section in ['2.3', '3', '7']:
                    payslip_lines = relevant_tax_slips.filtered(
                        lambda p: p.l10n_ch_after_departure_payment if year_delta else True).line_ids.filtered(
                        lambda pl: pl.salary_rule_id.l10n_ch_salary_certificate == section).sorted(
                        lambda pl: pl.salary_rule_id.l10n_ch_code)
                    text = ', '.join(sorted([w_t for w_t in set(payslip_lines.mapped('name'))]))
                    sum_value = sum(payslip_lines.mapped('total'))
                    if sum_value:
                        salary_certificate[key_path] = salary_certificate.get(key_path, []) + [{
                            "Text": text,
                            "Sum": self._amount2str(sum_value)
                        }]  # Salary Amount Type
                else:
                    sum_value = sum([line_values[mapped_rule.code][p.id]['total'] for p in relevant_tax_slips.filtered(
                        lambda p: p.l10n_ch_after_departure_payment if year_delta else True) for mapped_rule in
                                     rules_grouped_by_certificate_section[section]])
                    if sum_value:
                        if section in ["9", "12"]:
                            salary_certificate[key_path] = self._amount2str(-sum_value)
                        else:
                            salary_certificate[key_path] = self._amount2str(abs(sum_value))
                if int(section.split(".")[0]) < 8 and sum_value:
                    salary_certificate["GrossIncome"] = self._amount2str(
                        float(salary_certificate.get("GrossIncome", "0.00")) + sum_value)
                if sum_value:
                    any_amount = True

        salary_certificate["NetIncome"] = self._amount2str(float(salary_certificate.get("GrossIncome", "0.00")))

        # 14 - 15 : Standard Remarks
        if current_certificate.l10n_ch_cs_additional_text:
            salary_certificate["Remark"] = current_certificate.l10n_ch_cs_additional_text
        standard_remarks = dict()
        if rectificate_original_id and rectificate_original_date:
            standard_remarks["Rectificate"] = {
                "OriginalDate": format_date(self.env, rectificate_original_date, date_format='yyyy-MM-dd'),
                "OriginalDocID": rectificate_original_id
            }

        if standard_remarks and current_certificate.l10n_ch_certificate_type != 'TaxAnnuity':
            salary_certificate["StandardRemark"] = standard_remarks

        if any_amount:
            return salary_certificate
        else:
            return False

    def _get_yearly_retrospective(self, year, month, company_id, incomplete_declaration=False):
        swissdec_declaration = SwissdecDeclaration()
        mapped_payslips, line_values = self._get_yearly_mapped_payslips(
            domain=[("company_id", '=', company_id.id),
                    ("state", "in", ["paid", "done"]),
                    ('l10n_ch_social_insurance_id', '!=', False),
                    ('l10n_ch_laa_group', '!=', False),
                    ('l10n_ch_location_unit_id', '!=', False),
                    ('l10n_ch_compensation_fund_id', '!=', False)])
        yearly_values = self.env["l10n.ch.employee.yearly.values"].search([("year", '=', year), ('employee_id.company_id', '=', company_id.id)])
        swissdec_structure_rules = self.env.ref('l10n_ch_hr_payroll_elm_transmission.hr_payroll_structure_ch_elm').rule_ids
        rules_grouped_by_certificate_section = swissdec_structure_rules.grouped('l10n_ch_salary_certificate')
        caf_codes = swissdec_structure_rules.filtered(lambda r: r.l10n_ch_caf_statement and r.l10n_ch_caf_statement != "0").mapped("code")
        avs_splits = dict(self.env['l10n.ch.avs.splits']._read_group(domain=[('state', '=', 'confirmed')], groupby=['employee_id'], aggregates=['id:recordset']))
        mapped_qst_institutions = self.env["l10n.ch.source.tax.institution"].search([('company_id', '=', company_id.id)]).grouped("canton")

        global_avs_institutions = self.env["l10n.ch.social.insurance"]
        global_caf_institutions = self.env["l10n.ch.compensation.fund"]
        global_laa_institutions = self.env["l10n.ch.accident.insurance"]
        global_laac_institutions = self.env["l10n.ch.additional.accident.insurance"]
        global_ijm_institutions = self.env["l10n.ch.sickness.insurance"]
        global_txb_institutions = self.env["l10n.ch.source.tax.institution"]
        tax_institution = False

        staff = []

        agricole_company = company_id.l10n_ch_agricole_company
        global_txb_periods = defaultdict(lambda: {'from': None, 'until': None})

        for employee_id, years in mapped_payslips.items():
            for y, months in years.items():
                for m, payslips in months.items():
                    if m <= month or y < year:
                        for payslip in payslips.filtered(lambda p: p.l10n_ch_txb_code and p.l10n_ch_is_code and not p.l10n_ch_after_departure_payment):
                            applicable_date_start = max(payslip.date_from, payslip.contract_id.date_start)
                            applicable_date_start_s = format_date(self.env, applicable_date_start, date_format='yyyy-MM-dd')
                            applicable_date_end = min(payslip.date_to, payslip.contract_id.date_end if payslip.contract_id.date_end else payslip.date_to)
                            applicable_date_end_s = format_date(self.env, applicable_date_end, date_format='yyyy-MM-dd')
                            if global_txb_periods[applicable_date_start.year]['from'] is None or applicable_date_start_s < global_txb_periods[applicable_date_start.year]['from']:
                                global_txb_periods[applicable_date_start.year]['from'] = applicable_date_start_s

                            if global_txb_periods[applicable_date_end.year]['until'] is None or applicable_date_end_s > global_txb_periods[applicable_date_end.year]['until']:
                                global_txb_periods[applicable_date_end.year]['until'] = applicable_date_end_s

        for snapshot in yearly_values:
            ahv_avs_salaries = []
            fak_caf_salaries = []
            uvg_laa_salaries = []
            uvgz_laac_salaries = []
            ktg_amc_salaries = []
            tax_crossborder_salaries = []
            tax_salaries = []
            tax_annuities = []

            relevant_slips = self.env["hr.payslip"]
            year_delta = 0
            for m in mapped_payslips[snapshot.employee_id][snapshot.year]:
                if m <= month:
                    relevant_slips += mapped_payslips[snapshot.employee_id][snapshot.year][m].filtered(lambda p: not p.l10n_ch_after_departure_payment or (p.l10n_ch_after_departure_payment and p.date_to.year == snapshot.year and p.date_to.month <= month))

            if not relevant_slips:
                previous_year_payslips_paid_this_year = self.env["hr.payslip"]
                for m in mapped_payslips[snapshot.employee_id][snapshot.year-1]:
                    previous_year_payslips_paid_this_year += mapped_payslips[snapshot.employee_id][snapshot.year-1][m].filtered(lambda p: p.l10n_ch_after_departure_payment and p.date_to.year == snapshot.year and p.date_to.month <= month)
                if previous_year_payslips_paid_this_year:
                    for m in mapped_payslips[snapshot.employee_id][snapshot.year-1]:
                        relevant_slips += mapped_payslips[snapshot.employee_id][snapshot.year-1][m].filtered(lambda p: not p.l10n_ch_after_departure_payment)
                    relevant_slips += previous_year_payslips_paid_this_year
                if relevant_slips:
                    year_delta += 1

            # AVS Domain
            if relevant_slips:
                slips_grouped_by_contract = relevant_slips.grouped('contract_id')
                for contract, slips_c in slips_grouped_by_contract.items():
                    slips_grouped_by_institution = slips_c.grouped("l10n_ch_social_insurance_id")
                    for institution, slips_i in slips_grouped_by_institution.items():
                        slips_grouped_by_avs_status = slips_i.grouped("l10n_ch_avs_status")
                        for avs_status, slips_status in slips_grouped_by_avs_status.items():
                            start_avs = max(max(datetime.date(snapshot.year - year_delta, 1, 1), contract.date_start),
                                            min(slips_status.filtered(lambda p: not p.l10n_ch_after_departure_payment).mapped('date_from')))

                            if contract.date_end:
                                end_avs = min(contract.date_end, max(slips_status.filtered(lambda p: not p.l10n_ch_after_departure_payment).mapped('date_to')))
                            else:
                                end_avs = max(slips_grouped_by_avs_status[avs_status].filtered(lambda p: not p.l10n_ch_after_departure_payment).mapped('date_to'))

                            avs_base = 0
                            avs_salary = 0
                            avs_open_salary = 0
                            ac_salary = 0
                            ac_open_salary = 0
                            acc_salary = 0

                            for avs_status_slip in slips_status.filtered(lambda p: p.l10n_ch_after_departure_payment if year_delta else True):
                                avs_base += line_values['AVSBASE'][avs_status_slip.id]['total']
                                avs_salary += line_values['AVSSALARY'][avs_status_slip.id]['total']
                                ac_salary += line_values['ACSALARY'][avs_status_slip.id]['total']
                                acc_salary += line_values['ACCSALARY'][avs_status_slip.id]['total']
                                avs_open_salary += line_values['AVSOPEN'][avs_status_slip.id]['total']
                                ac_open_salary += line_values['ACOPEN'][avs_status_slip.id]['total']

                            ahv_avs_salary = swissdec_declaration.create_ahv_avs_salary(
                                institution_id=institution,
                                accounting_from=format_date(self.env, start_avs, date_format='yyyy-MM-dd'),
                                accounting_to=format_date(self.env, end_avs, date_format='yyyy-MM-dd'),
                                avs_salary=avs_salary,
                                ac_salary=ac_salary,
                                acc_salary=acc_salary,
                                avs_open=avs_open_salary,
                                ac_open=ac_open_salary,
                                splits=avs_splits.get(snapshot.employee_id, False),
                                ceo_rel=snapshot.employee_id.l10n_ch_relationship_ceo if agricole_company else False,
                            )

                            if ahv_avs_salary:
                                ahv_avs_salary.update({
                                    **self.env['l10n.ch.employee.monthly.values']._get_additional_avs_values(avs_base, avs_status)
                                })
                                ahv_avs_salaries.append(ahv_avs_salary)
                                global_avs_institutions += institution

                    # LAA DOMAIN
                    # We could have different codes under the same contract : A1 A1 A2 A2 A3 A1 A1 -> They need to be grouped up like this :
                    # [A1, A1] [A2, A2] [A3] [A1, A1]
                    laa_group_slices = defaultdict(list)
                    start_index = 0
                    laa_slips = slips_c.sorted('date_to')
                    for i in range(1, len(laa_slips)):
                        current_laa_code = laa_slips[i].l10n_ch_laa_group.group_unit + laa_slips[i].laa_solution_number
                        previous_laa_code = laa_slips[i - 1].l10n_ch_laa_group.group_unit + laa_slips[i - 1].laa_solution_number
                        if current_laa_code != previous_laa_code:
                            solution_code = laa_slips[start_index].l10n_ch_laa_group.group_unit + laa_slips[start_index].laa_solution_number
                            insurance_id = laa_slips[start_index].l10n_ch_laa_group.insurance_id
                            laa_group_slices[(insurance_id, solution_code)].append(laa_slips[start_index:i])
                            start_index = i
                    solution_code = laa_slips[start_index].l10n_ch_laa_group.group_unit + laa_slips[start_index].laa_solution_number
                    insurance_id = laa_slips[start_index].l10n_ch_laa_group.insurance_id
                    laa_group_slices[(insurance_id, solution_code)].append(laa_slips[start_index:len(laa_slips)])

                    for code in laa_group_slices:
                        for code_period_slips in laa_group_slices[code]:
                            laa_gross = 0
                            laa_base = 0
                            laa_salary = 0

                            start_laa = max(max(datetime.date(snapshot.year - year_delta, 1, 1), contract.date_start),
                                            min(code_period_slips.filtered(lambda p: not p.l10n_ch_after_departure_payment).mapped('date_from')))

                            if contract.date_end:
                                end_laa = min(contract.date_end, max(code_period_slips.filtered(lambda p: not p.l10n_ch_after_departure_payment).mapped('date_to')))
                            else:
                                end_laa = max(code_period_slips.filtered(lambda p: not p.l10n_ch_after_departure_payment).mapped('date_to'))

                            for laa_slip in code_period_slips.filtered(lambda p: p.l10n_ch_after_departure_payment if year_delta else True):
                                laa_gross += line_values['GROSS_SALARY'][laa_slip.id]['total']
                                laa_base += line_values['LAABASE'][laa_slip.id]['total']
                                laa_salary += line_values['LAASALARY'][laa_slip.id]['total']
                            uvg_laa_salary = {
                                "institutionIDRef": swissdec_declaration.get_institution_id_ref(code[0]),
                                "AccountingTime": {
                                    "from": format_date(self.env, start_laa, date_format='yyyy-MM-dd'),
                                    "until": format_date(self.env, end_laa, date_format='yyyy-MM-dd')
                                },
                                "UVG-LAA-Code": code[1]
                            }

                            uvg_laa_salary["UVG-LAA-GrossSalary"] = self._amount2str(laa_gross)
                            uvg_laa_salary["UVG-LAA-BaseSalary"] = self._amount2str(laa_base)
                            uvg_laa_salary["UVG-LAA-ContributorySalary"] = self._amount2str(laa_salary)
                            if laa_gross or laa_base or laa_salary:
                                uvg_laa_salaries.append(uvg_laa_salary)
                                global_laa_institutions += code[0]

                    # LAAC DOMAIN
                    # Same logic as LAA but more complicated since we have a many2many and insurance position should not influence
                    # grouping
                    laac_group_slices = defaultdict(list)
                    laac_slips = slips_grouped_by_contract[contract].sorted('date_to')
                    all_laac_codes = laac_slips.mapped('l10n_ch_additional_accident_insurance_line_ids')
                    for laac_id in all_laac_codes:
                        laac_sub_group = []
                        for slip in laac_slips:
                            if laac_id in slip.l10n_ch_additional_accident_insurance_line_ids:
                                laac_sub_group.append(
                                    (slip.l10n_ch_additional_accident_insurance_line_ids.ids.index(laac_id.id) + 1, slip))
                            else:
                                if laac_sub_group:
                                    laac_group_slices[(laac_id.insurance_id, laac_id.solution_code)].append(laac_sub_group)
                                    laac_sub_group = []
                        if laac_sub_group:
                            laac_group_slices[(laac_id.insurance_id, laac_id.solution_code)].append(laac_sub_group)

                    for laac_code in laac_group_slices:
                        for laac_code_period_slips in laac_group_slices[laac_code]:
                            laac_base = 0
                            laac_salary = 0

                            start_laac = max(max(datetime.date(snapshot.year - year_delta, 1, 1), contract.date_start),
                                             min([p for p in laac_code_period_slips if not p[1].l10n_ch_after_departure_payment], key=lambda p: p[1].date_from)[1].date_from)

                            if contract.date_end:
                                end_laac = min(contract.date_end, max([p for p in laac_code_period_slips if not p[1].l10n_ch_after_departure_payment], key=lambda p: p[1].date_to)[1].date_to)
                            else:
                                end_laac = max([p for p in laac_code_period_slips if not p[1].l10n_ch_after_departure_payment], key=lambda p: p[1].date_to)[1].date_to


                            for position, slip in laac_code_period_slips:
                                if not year_delta or (year_delta and slip.l10n_ch_after_departure_payment):
                                    laac_base += line_values['LAACBASE'][slip.id]['total']
                                    laac_salary += line_values[f'LAACSALARY{position}'][slip.id]['total']

                            uvgz_laac_salary = {
                                "institutionIDRef": swissdec_declaration.get_institution_id_ref(laac_code[0]),
                                "AccountingTime": {
                                    "from": format_date(self.env, start_laac, date_format='yyyy-MM-dd'),
                                    "until": format_date(self.env, end_laac, date_format='yyyy-MM-dd')
                                },
                                "UVGZ-LAAC-Code": laac_code[1]
                            }
                            uvgz_laac_salary["UVGZ-LAAC-BaseSalary"] = self._amount2str(laac_base)
                            uvgz_laac_salary["UVGZ-LAAC-ContributorySalary"] = self._amount2str(laac_salary)

                            if laac_base or laac_salary:
                                uvgz_laac_salaries.append(uvgz_laac_salary)
                                global_laac_institutions += laac_code[0]

                    # IJM DOMAIN
                    # Completely Analogous to LAAC Domain
                    ijm_group_slices = defaultdict(list)
                    ijm_slips = slips_grouped_by_contract[contract].sorted('date_to')
                    all_ijm_codes = ijm_slips.mapped('l10n_ch_sickness_insurance_line_ids')
                    for ijm_id in all_ijm_codes:
                        ijm_sub_group = []
                        for slip in ijm_slips:
                            if ijm_id in slip.l10n_ch_sickness_insurance_line_ids:
                                ijm_sub_group.append(
                                    (slip.l10n_ch_sickness_insurance_line_ids.ids.index(ijm_id.id) + 1, slip))
                            else:
                                if ijm_sub_group:
                                    ijm_group_slices[(ijm_id.insurance_id, ijm_id.solution_code)].append(ijm_sub_group)
                                    ijm_sub_group = []
                        if ijm_sub_group:
                            ijm_group_slices[(ijm_id.insurance_id, ijm_id.solution_code)].append(ijm_sub_group)

                    for ijm_code in ijm_group_slices:
                        for ijm_code_period_slips in ijm_group_slices[ijm_code]:
                            ijm_base = 0
                            ijm_salary = 0

                            start_ijm = max(max(datetime.date(snapshot.year - year_delta, 1, 1), contract.date_start),
                                             min([p for p in ijm_code_period_slips if
                                                  not p[1].l10n_ch_after_departure_payment],
                                                 key=lambda p: p[1].date_from)[1].date_from)

                            if contract.date_end:
                                end_ijm = min(contract.date_end, max([p for p in ijm_code_period_slips if not p[1].l10n_ch_after_departure_payment], key=lambda p: p[1].date_to)[1].date_to)
                            else:
                                end_ijm = max([p for p in ijm_code_period_slips if not p[1].l10n_ch_after_departure_payment], key=lambda p: p[1].date_to)[1].date_to

                            for position, slip in ijm_code_period_slips:
                                if not year_delta or (year_delta and slip.l10n_ch_after_departure_payment):
                                    ijm_base += line_values['AVSSALARY'][slip.id]['total'] + line_values['AVSOPEN'][slip.id]['total']
                                    ijm_salary += line_values[f'IJMSALARY{position}'][slip.id]['total']

                            ktg_amc_salary = {
                                "institutionIDRef": swissdec_declaration.get_institution_id_ref(ijm_code[0]),
                                "AccountingTime": {
                                    "from": format_date(self.env, start_ijm, date_format='yyyy-MM-dd'),
                                    "until": format_date(self.env, end_ijm, date_format='yyyy-MM-dd')
                                },
                                "KTG-AMC-Code": ijm_code[1]
                            }
                            ktg_amc_salary["Reference-AHV-AVS-Salary"] = self._amount2str(ijm_base)
                            ktg_amc_salary["KTG-AMC-ContributorySalary"] = self._amount2str(ijm_salary)

                            if ijm_base or ijm_salary:
                                ktg_amc_salaries.append(ktg_amc_salary)
                                global_ijm_institutions += ijm_code[0]


                    # CAF Domain
                    slips_grouped_by_caf = slips_grouped_by_contract[contract].grouped("l10n_ch_compensation_fund_id")
                    for caf in slips_grouped_by_caf:
                        slips_grouped_by_work_canton = slips_grouped_by_caf[caf].grouped(lambda p: p.l10n_ch_location_unit_id.canton)
                        for canton in slips_grouped_by_work_canton:
                            start_caf = max(max(datetime.date(snapshot.year - year_delta, 1, 1), contract.date_start),
                                            min(slips_grouped_by_work_canton[canton].filtered(lambda p: not p.l10n_ch_after_departure_payment).mapped('date_from')))
                            if contract.date_end:
                                end_caf = min(contract.date_end, max(slips_grouped_by_work_canton[canton].filtered(lambda p: not p.l10n_ch_after_departure_payment).mapped('date_to')))
                            else:
                                end_caf = max(slips_grouped_by_work_canton[canton].filtered(lambda p: not p.l10n_ch_after_departure_payment).mapped('date_to'))

                            avs_salary = 0
                            reference_avs_salary = 0
                            caf_amount = 0
                            for slip in slips_grouped_by_work_canton[canton].filtered(lambda p: p.l10n_ch_after_departure_payment if year_delta else True):
                                avs_salary += line_values['AVSSALARY'][slip.id]['total']
                                reference_avs_salary += line_values['AVSSALARY'][slip.id]['total'] + line_values['AVSOPEN'][slip.id]['total']
                                caf_amount += sum([line_values[code][slip.id]['total'] for code in caf_codes])

                            if avs_salary:
                                fak_caf_salaries.append({
                                    "institutionIDRef": swissdec_declaration.get_institution_id_ref(caf),
                                    "FAK-CAF-Period": {
                                        "from": format_date(self.env, start_caf, date_format='yyyy-MM-dd'),
                                        "until": format_date(self.env, end_caf, date_format='yyyy-MM-dd'),
                                    },
                                    "FAK-CAF-ContributorySalary": self._amount2str(avs_salary),
                                    "FAK-CAF-FamilyIncomeSupplement": {
                                        "FAK-CAF-FamilyIncomeSupplementPerPerson": self._amount2str(caf_amount)
                                    },
                                    "FAK-CAF-WorkplaceCanton": canton
                                })
                                global_caf_institutions += caf

                    for contract in slips_grouped_by_contract:
                        txb_slips = defaultdict(list)
                        relevant_txb_slips = slips_grouped_by_contract[contract].filtered(
                            lambda p: p.l10n_ch_txb_code).sorted(
                            'date_to')
                        start_index = 0
                        for i in range(1, len(relevant_txb_slips)):
                            if relevant_txb_slips[i].l10n_ch_txb_code != relevant_txb_slips[i - 1].l10n_ch_txb_code:
                                st_canton = relevant_txb_slips[start_index].l10n_ch_txb_code
                                txb_slips[st_canton].append(relevant_txb_slips[start_index:i])
                                start_index = i
                        if start_index < len(relevant_txb_slips):
                            st_canton = relevant_txb_slips[start_index].l10n_ch_txb_code
                            txb_slips[st_canton].append(relevant_txb_slips[start_index:])

                        for st_c in txb_slips:
                            for slip_period in txb_slips[st_c]:
                                start_txb = max(max(datetime.date(snapshot.year - year_delta, 1, 1), contract.date_start),
                                                min(slip_period.filtered(lambda p: not p.l10n_ch_after_departure_payment).mapped('date_from')))
                                if contract.date_end:
                                    end_txb = min(contract.date_end, max(slip_period.filtered(lambda p: not p.l10n_ch_after_departure_payment).mapped('date_to')))
                                else:
                                    end_txb  =max(slip_period.filtered(lambda p: not p.l10n_ch_after_departure_payment).mapped('date_to'))

                                is_salary = sum([line_values['ISSALARY'][p.id]['total'] for p in slip_period.filtered(lambda p: p.l10n_ch_after_departure_payment if year_delta else True)])
                                is_deductions = sum(slip_period.filtered(lambda p: p.l10n_ch_after_departure_payment if year_delta else True).line_ids.filtered(
                                    lambda pl: pl.salary_rule_id.l10n_ch_salary_certificate == "12").mapped('total'))
                                insurance_contributions = sum(slip_period.filtered(lambda p: p.l10n_ch_after_departure_payment if year_delta else True).line_ids.filtered(
                                    lambda pl: pl.salary_rule_id.l10n_ch_salary_certificate == "9").mapped('total'))
                                txb_country, st_canton = st_c.split('-')
                                if txb_country == "IT":
                                    txb_salary = {
                                        "institutionIDRef": swissdec_declaration.get_institution_id_ref(
                                            mapped_qst_institutions.get(st_canton)),
                                        "Period": {
                                            "from": format_date(self.env, start_txb, date_format='yyyy-MM-dd'),
                                            "until": format_date(self.env, end_txb, date_format='yyyy-MM-dd')
                                        },
                                        "TaxAtSourceCanton": st_canton,
                                        "ResidenceAbroadCountry": txb_country,
                                        "TaxID": snapshot.employee_id.l10n_ch_foreign_tax_id,
                                        "PlaceOfBirth": snapshot.employee_id.place_of_birth,
                                        "TaxableEarning": self._amount2str(is_salary),
                                        "DeductionAtSource": self._amount2str(-is_deductions),
                                        "CrossborderValidAsOf": format_date(self.env,
                                                                            snapshot.employee_id.l10n_ch_cross_border_start,
                                                                            date_format='yyyy-MM-dd'),
                                        "AHV-ALV-NBUV-AVS-AC-AANP-Contribution": self._amount2str(
                                            -insurance_contributions)
                                    }
                                else:
                                    txb_salary = {
                                        "institutionIDRef": swissdec_declaration.get_institution_id_ref(
                                            mapped_qst_institutions.get(st_canton)),
                                        "Period": {
                                            "from": format_date(self.env, start_txb, date_format='yyyy-MM-dd'),
                                            "until": format_date(self.env, end_txb, date_format='yyyy-MM-dd')
                                        },
                                        "TaxAtSourceCanton": st_canton,
                                        "ResidenceAbroadCountry": txb_country,
                                        "TaxableEarning": self._amount2str(is_salary),
                                    }
                                    # ELM 5.3 France - Switzerland convention on declaring teleworking
                                    if txb_country == "FR":
                                        txb_salary.update({
                                            **snapshot.monthly_value_ids[month - 1]._get_additional_txb_values()
                                        })
                                global_txb_institutions += mapped_qst_institutions.get(st_canton)
                                tax_crossborder_salaries.append(txb_salary)

                all_profiles = snapshot.employee_id.l10n_ch_salary_certificate_profiles.sorted('valid_from')
                for i, current_certificate in enumerate(all_profiles):
                    next_profile_start = datetime.date(9999, 12, 31)
                    if i + 1 < len(all_profiles):
                        next_profile = all_profiles[i + 1]
                        next_profile_start = next_profile.valid_from
                    relevant_tax_slips = relevant_slips.filtered(lambda p: p.date_from >= current_certificate.valid_from and p.date_to < next_profile_start)
                    if relevant_tax_slips:
                        first_slip = min(relevant_tax_slips.filtered(lambda p: not p.l10n_ch_after_departure_payment),
                                         key=lambda p: p.date_from)
                        last_slip = max(relevant_tax_slips.filtered(lambda p: not p.l10n_ch_after_departure_payment),
                                        key=lambda p: p.date_to)
                        last_monthly_value = snapshot.monthly_value_ids.filtered(lambda s: s.month == last_slip.date_to.month)
                        period_from = max(first_slip.contract_id.date_start, datetime.date(snapshot.year - year_delta, 1, 1))
                        period_to = min(last_slip.date_to, last_slip.contract_id.date_end or datetime.date(snapshot.year - year_delta, 12, 31))
                        period_from = max(period_from, current_certificate.valid_from)
                        period_to = min(period_to, next_profile_start)
                        if current_certificate.l10n_ch_certificate_type == 'TaxSalary':
                            salary_certificate = self._create_wage_statement(current_certificate, period_from, period_to, relevant_tax_slips, line_values, last_monthly_value, rules_grouped_by_certificate_section, year_delta)
                        else:
                            salary_certificate = self._create_pension_statement(current_certificate, period_from, period_to, relevant_tax_slips, line_values, last_monthly_value, rules_grouped_by_certificate_section, year_delta)

                        if salary_certificate:
                            if current_certificate.l10n_ch_certificate_type == 'TaxAnnuity':
                                tax_annuities.append(self._flat_dict_to_nest_dict(salary_certificate))
                            else:
                                tax_salaries.append(self._flat_dict_to_nest_dict(salary_certificate))

            current_person = snapshot.monthly_value_ids.filtered(lambda m: m.month == month)
            if current_person.person:
                salaries = {}
                if ahv_avs_salaries:
                    salaries["AHV-AVS-Salaries"] = {
                        "AHV-AVS-Salary": ahv_avs_salaries
                    }
                if fak_caf_salaries:
                    salaries["FAK-CAF-Salaries"] = {
                        "FAK-CAF-Salary": fak_caf_salaries
                    }
                if uvg_laa_salaries:
                    salaries["UVG-LAA-Salaries"] = {
                        "UVG-LAA-Salary": uvg_laa_salaries
                    }
                if uvgz_laac_salaries:
                    salaries["UVGZ-LAAC-Salaries"] = {
                        "UVGZ-LAAC-Salary": uvgz_laac_salaries
                    }
                if ktg_amc_salaries:
                    salaries["KTG-AMC-Salaries"] = {
                        "KTG-AMC-Salary": ktg_amc_salaries
                    }
                if tax_salaries or tax_annuities:
                    salaries["TaxSalaries"] = {}
                    if tax_salaries:
                        salaries["TaxSalaries"]["TaxSalary"] = tax_salaries
                    if tax_annuities:
                        salaries["TaxSalaries"]["TaxAnnuity"] = tax_annuities
                    tax_institution = [SwissdecInstitution("Tax")]
                if tax_crossborder_salaries:
                    salaries["TaxCrossborderSalaries"] = {
                        "TaxCrossborderSalary": tax_crossborder_salaries
                    }


                if salaries:
                    staff.append({
                        **current_person.person,
                        **salaries
                    })
        if staff:
            staff_declaration = {
                "Staff": {
                    "Person": staff
                }
            }
            institutions_to_process = list(set(global_avs_institutions)) + list(set(global_caf_institutions)) + list(set(global_ijm_institutions)) + list(set(global_laa_institutions)) + list(set(global_laac_institutions)) + list(set(global_txb_institutions))
            if tax_institution:
                institutions_to_process += tax_institution
            declaration = {
                **swissdec_declaration.get_company_description(company_id),
                **staff_declaration,
                **swissdec_declaration.get_institutions(institutions_to_process, txb=True, incomplete_declaration=incomplete_declaration),
                "SalaryCounters": swissdec_declaration.get_salary_tag_counter(staff_declaration),
                "SalaryTotals": swissdec_declaration.get_salary_totals(staff, uvg_month=month, uvg_year=year, global_txb_periods=global_txb_periods)
            }
            allowed_institutions = {
                "AVS": set(global_avs_institutions.ids),
                "CAF": set(global_caf_institutions.ids),
                "LAA": set(global_laa_institutions.ids),
                "LAAC": set(global_laac_institutions.ids),
                "IJM": set(global_ijm_institutions.ids),
                "TXB": set(global_txb_institutions.ids),
                "Tax": bool(tax_institution)
            }
        else:
            declaration = {}
            allowed_institutions = {}

        return declaration, allowed_institutions

    def _get_salary_rectificates(self, year, month, company_id, original_date, to_replace):
        swissdec_declaration = SwissdecDeclaration()
        mapped_payslips, line_values = self._get_yearly_mapped_payslips(domain=[("company_id", '=', company_id.id), ("state", "in", ["paid", "done"])])
        yearly_values = self.env["l10n.ch.employee.yearly.values"].search([("year", '=', year), ('employee_id.company_id', '=', company_id.id)])
        swissdec_structure_rules = self.env.ref('l10n_ch_hr_payroll_elm_transmission.hr_payroll_structure_ch_elm').rule_ids
        rules_grouped_by_certificate_section = swissdec_structure_rules.grouped('l10n_ch_salary_certificate')

        staff = []

        for snapshot in yearly_values.filtered(lambda s: s.employee_id.registration_number in to_replace):
            tax_salaries = []
            tax_annuities = []
            relevant_slips = self.env["hr.payslip"]
            year_delta = 0
            for m in mapped_payslips[snapshot.employee_id][snapshot.year]:
                if m <= month:
                    relevant_slips += mapped_payslips[snapshot.employee_id][snapshot.year][m].filtered(lambda p: not p.l10n_ch_after_departure_payment or (p.l10n_ch_after_departure_payment and p.date_to.year == snapshot.year and p.date_to.month <= month))

            if not relevant_slips:
                previous_year_payslips_paid_this_year = self.env["hr.payslip"]
                for m in mapped_payslips[snapshot.employee_id][snapshot.year-1]:
                    previous_year_payslips_paid_this_year += mapped_payslips[snapshot.employee_id][snapshot.year-1][m].filtered(lambda p: p.l10n_ch_after_departure_payment and p.date_to.year == snapshot.year and p.date_to.month <= month)
                if previous_year_payslips_paid_this_year:
                    for m in mapped_payslips[snapshot.employee_id][snapshot.year-1]:
                        relevant_slips += mapped_payslips[snapshot.employee_id][snapshot.year-1][m].filtered(lambda p: not p.l10n_ch_after_departure_payment)
                    relevant_slips += previous_year_payslips_paid_this_year
                if relevant_slips:
                    year_delta += 1

            all_profiles = snapshot.employee_id.l10n_ch_salary_certificate_profiles.sorted('valid_from')
            for i, current_certificate in enumerate(all_profiles):
                next_profile_start = datetime.date(9999, 12, 31)
                if i + 1 < len(all_profiles):
                    next_profile = all_profiles[i + 1]
                    next_profile_start = next_profile.valid_from
                relevant_tax_slips = relevant_slips.filtered(
                    lambda p: p.date_from >= current_certificate.valid_from and p.date_to < next_profile_start)
                first_slip = min(relevant_tax_slips.filtered(lambda p: not p.l10n_ch_after_departure_payment),
                                 key=lambda p: p.date_from)
                last_slip = max(relevant_tax_slips.filtered(lambda p: not p.l10n_ch_after_departure_payment),
                                key=lambda p: p.date_to)
                last_monthly_value = snapshot.monthly_value_ids.filtered(lambda s: s.month == last_slip.date_to.month)
                period_from = max(first_slip.contract_id.date_start, datetime.date(snapshot.year - year_delta, 1, 1))
                period_to = min(last_slip.date_to,
                                last_slip.contract_id.date_end or datetime.date(snapshot.year - year_delta, 12, 31))
                period_from = max(period_from, current_certificate.valid_from)
                period_to = min(period_to, next_profile_start)


                if current_certificate.l10n_ch_certificate_type == 'TaxSalary':
                    salary_certificate = self._create_wage_statement(current_certificate, period_from, period_to,
                                                                     relevant_tax_slips, line_values,
                                                                     last_monthly_value,
                                                                     rules_grouped_by_certificate_section, year_delta,
                                                                     rectificate_original_id=to_replace.get(snapshot.employee_id.registration_number)[-1].get("DocID"),
                                                                     rectificate_original_date=original_date)
                else:
                    salary_certificate = self._create_pension_statement(current_certificate, period_from, period_to,
                                                                        relevant_tax_slips, line_values,
                                                                        last_monthly_value,
                                                                        rules_grouped_by_certificate_section,
                                                                        year_delta,
                                                                        rectificate_original_id=to_replace.get(snapshot.employee_id.registration_number)[-1].get("DocID"),
                                                                        rectificate_original_date=original_date)

                if salary_certificate:
                    if current_certificate.l10n_ch_certificate_type == 'TaxAnnuity':
                        tax_annuities.append(self._flat_dict_to_nest_dict(salary_certificate))
                    else:
                        tax_salaries.append(self._flat_dict_to_nest_dict(salary_certificate))


            current_person = snapshot.monthly_value_ids.filtered(lambda m: m.month == month)
            if current_person.person:
                salaries = {}
                if tax_salaries or tax_annuities:
                    salaries["TaxSalaries"] = {}
                    if tax_salaries:
                        salaries["TaxSalaries"]["TaxSalary"] = tax_salaries
                    if tax_annuities:
                        salaries["TaxSalaries"]["TaxAnnuity"] = tax_annuities

                if salaries:
                    staff.append({
                        **current_person.person,
                        **salaries
                    })
        if staff:
            staff_declaration = {
                "Staff": {
                    "Person": staff
                }
            }
            institutions_to_process = [SwissdecInstitution("Tax")]
            declaration = {
                **swissdec_declaration.get_company_description(company_id),
                **staff_declaration,
                "SalaryCounters": swissdec_declaration.get_salary_tag_counter(staff_declaration),
                "SalaryTotals": swissdec_declaration.get_salary_totals(staff)
            }
            allowed_institutions = {
                "Tax": True
            }
        else:
            declaration = {}
            allowed_institutions = {}

        return declaration, allowed_institutions
