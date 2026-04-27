# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools.float_utils import float_compare


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    l10n_au_tfn_declaration = fields.Selection(
        selection=[
            ("provided", "Declaration provided"),
            ("000000000", "Declaration not completed, employee did not provide TFN, employee promised declaration more than 28 days ago"),
            ("111111111", "Employee applied for TFN but didn't receive it yet, less than 28 days ago"),
            ("333333333", "Employee under 18 and earns less than 350$ weekly"),
            ("444444444", "Employee is recipient of social security, service pension or benefit, may be exempt from TFN")],
        string="TFN Status",
        default="000000000",
        required=True,
        groups="hr.group_hr_user",
        help="TFN Declaration status of the employee. All options except 'Declaration not completed...' will be treated as TFN provided.")
    l10n_au_tfn = fields.Char(
        string="Tax File Number",
        compute="_compute_l10n_au_tfn",
        readonly=False,
        store=True,
        groups="hr.group_hr_user")
    l10n_au_abn = fields.Char(
        string="Australian Business Number",
        compute="_compute_l10n_au_abn",
        inverse="_inverse_l10n_au_abn",
        store=True,
        readonly=False,
        groups="hr.group_hr_user")
    l10n_au_nat_3093_amount = fields.Float(
        string="Annual Tax Offset",
        groups="hr.group_hr_user",
        help="Amount of tax offset the employee entered in his NAT3093 withholding declaration, 0 if the employee did not present a declaration")
    l10n_au_extra_pay = fields.Boolean(
        string="Withhold for Extra Pay",
        groups="hr.group_hr_user",
        help="Whether the employee wants additional withholding in case of 53 weekly pays or 27 fortnightly pays in a year")
    l10n_au_previous_payroll_id = fields.Char(
        string="Previous Payroll ID",
        groups="hr.group_hr_user")
    l10n_au_payroll_id = fields.Char(
        string="Payroll ID",
        groups="hr.group_hr_user")
    l10n_au_training_loan = fields.Boolean(
        string="HELP / STSL",
        groups="hr.group_hr_user",
        help="Whether the employee is a Study Training Support Loan (STSL) recipient")
    l10n_au_medicare_variation_form = fields.Binary(string="Medicare Variation Form", attachment=True, groups="hr.group_hr_user")
    l10n_au_medicare_variation_form_filename = fields.Char(groups="hr.group_hr_user")
    l10n_au_medicare_exemption = fields.Selection(
        selection=[
            ("X", "None"),
            ("H", "Half"),
            ("F", "Full")],
        string="Medicare levy exemption",
        default="X",
        required=True,
        groups="hr.group_hr_user")
    l10n_au_medicare_surcharge = fields.Selection(
        selection=[
            ("X", "0%"),
            ("1", "1%"),
            ("2", "1.25%"),
            ("3", "1.5%")],
        string="Medicare levy surcharge",
        default="X",
        groups="hr.group_hr_user",
        required=True)
    l10n_au_medicare_reduction = fields.Selection(
        selection=[
            ("X", "Not Applicable"),
            ("0", "Spouse Only"),
            ("1", "1 Child"),
            ("2", "2 Children"),
            ("3", "3 Children"),
            ("4", "4 Children"),
            ("5", "5 Children"),
            ("6", "6 Children"),
            ("7", "7 Children"),
            ("8", "8 Children"),
            ("9", "9 Children"),
            ("A", "10+ Children"),
        ],
        string="Medicare levy reduction",
        compute="_compute_l10n_au_medicare_reduction",
        store=True,
        readonly=False,
        required=True,
        default="X",
        groups="hr.group_hr_user",
        help="Medicare levy reduction, dependent on marital status and number of children")
    l10n_au_tax_free_threshold = fields.Boolean(
        string="Tax-free Threshold",
        groups="hr.group_hr_user")
    l10n_au_super_account_ids = fields.One2many(
        "l10n_au.super.account",
        "employee_id",
        string="Super Accounts",
        groups="hr.group_hr_user",
    )
    l10n_au_child_support_deduction = fields.Float(
        string="Child Support Deduction",
        groups="hr.group_hr_user",
        help="Amount that has to be deducted every pay period, subject to Protected Earnings Amount (PEA)")
    l10n_au_child_support_garnishee_amount = fields.Float(
        string="Child Support Garnishee Amount %",
        groups="hr.group_hr_user")
    super_account_warning = fields.Text(compute="_compute_proportion_warnings", groups="hr.group_hr_user")
    l10n_au_other_names = fields.Char("Other Given Names", groups="hr.group_hr_user")
    l10n_au_employment_basis_code = fields.Selection(
        selection=[
            ("F", "Full time"),
            ("P", "Part time"),
            ("C", "Casual"),
            ("L", "Labour hire"),
            ("V", "Voluntary agreement"),
            ("D", "Death beneficiary"),
            ("N", "Non-employee")],
        string="Employment Type",
        default="F",
        required=True,
        groups="hr.group_hr_user"
    )
    l10n_au_tax_treatment_category = fields.Selection(
        selection=[
            ("R", "Regular"),
            ("A", "Actor"),
            ("C", "Horticulture & Shearing"),
            ("S", "Seniors & Pensioners"),
            ("H", "Working Holiday Makers"),
            ("W", "Seasonal Worker Program"),
            ("F", "Foreign Resident"),
            ("N", "No TFN"),
            ("D", "ATO-defined"),
            ("V", "Voluntary Agreement")],
        default="R",
        required=True,
        string="Tax Treatment Category",
        groups="hr.group_hr_user")
    l10n_au_income_stream_type = fields.Selection(
        selection=[
            ("SAW", "Salary and wages"),
            ("CHP", "Closely held payees"),
            ("IAA", "Inbound assignees to Australia"),
            ("WHM", "Working holiday makers"),
            ("SWP", "Seasonal worker programme"),
            ("FEI", "Foreign employment income"),
            ("JPD", "Joint petroleum development area"),
            ("VOL", "Voluntary agreement"),
            ("LAB", "Labour hire"),
            ("OSP", "Other specified payments")],
        string="Income Stream Type", default="SAW",
        compute="_compute_l10n_au_income_stream_type",
        precompute=True,
        store=True, readonly=False, required=True,
        groups="hr.group_hr_user")
    l10n_au_tax_treatment_option_actor = fields.Selection(
        selection=[
            ("D", "Daily Performer"),
            ("P", "Promotional Activity")
        ], string="Actor Option", groups="hr.group_hr_user")
    l10n_au_less_than_3_performance = fields.Boolean(string="Less than 3 Performances", groups="hr.group_hr_user")
    l10n_au_tax_treatment_option_voluntary = fields.Selection(
        selection=[
            ("C", "Commissioner's Instalment Rate"),
            ("O", "Other Rate"),
        ], string="Voluntary Agreement Option", groups="hr.group_hr_user")
    l10n_au_tax_treatment_option_seniors = fields.Selection(
        selection=[
            ("S", "Single"),
            ("M", "Married"),
            ("I", "Illness-separated"),
        ], string="Seniors Option", groups="hr.group_hr_user")
    l10n_au_comissioners_installment_rate = fields.Float(
        string="Commissioner's Instalment Rate", groups="hr.group_hr_user")
    l10n_au_tax_treatment_code = fields.Char(
        string="Tax Code", store=True,
        compute="_compute_l10n_au_tax_treatment_code",
        groups="hr.group_hr_user"
    )
    l10n_au_work_country_id = fields.Many2one(
        "res.country", string="Country", help="Country where the work is performed", groups="hr.group_hr_user"
    )
    l10n_au_withholding_variation = fields.Selection(
        selection=[
            ("none", "None"),
            ("salaries", "Salaries"),
            ("leaves", "Salaries and Unused Leaves"),
        ],
        string="Withholding Variation",
        default="none",
        groups="hr.group_hr_user",
        required=True,
        help="Employee has a custom withholding rate.",
    )
    l10n_au_withholding_variation_amount = fields.Float(string="Withholding Variation Rate", groups="hr.group_hr_user")
    l10n_au_additional_withholding_amount = fields.Monetary(
        string="Additional Withholding Amount",
        groups="hr.group_hr_user",
        help="Additional amount will be withheld from the employee's salary after PAYG withholding. (Schedule 14)")

    _sql_constraints = [
        ("l10n_au_child_support_garnishee_amount_span",
        "CHECK(l10n_au_child_support_garnishee_amount >= 0 AND l10n_au_child_support_garnishee_amount <= 1)",
        "Child Support Garnishee is a percentage and should have a value between 0 and 100."),
    ]
    # == CRUD Methods ==

    def write(self, vals):
        if 'l10n_au_tax_treatment_category' in vals and vals.get('l10n_au_tax_treatment_category') != 'H':
            vals['l10n_au_nat_3093_amount'] = 0
        return super().write(vals)

    # == Constraints ==

    @api.constrains("private_country_id", "l10n_au_income_stream_type")
    def _check_l10n_au_work_country(self):
        for rec in self:
            if rec.country_id.code in ["AU", False] and rec.l10n_au_income_stream_type in ["IAA", "WHM"]:
                raise ValidationError(_(
                    "Inbound assignees to Australia and Working Holiday Makers must have a Nationality set other than Australia."
                ))

    @api.constrains(
        "l10n_au_tax_treatment_category",
        "l10n_au_income_stream_type",
        "l10n_au_tfn_declaration",
        "l10n_au_tax_free_threshold",
        "is_non_resident",
    )
    def _check_l10n_au_tax_treatment(self):
        for rec in self:
            if rec.company_country_code != "AU":
                continue
            # TFN Declaration Constraints
            elif rec.l10n_au_tfn_declaration != "000000000" and rec.l10n_au_tax_treatment_category == "N":
                raise ValidationError(_("The Employee has a TFN provided so the No TFN tax treatment category cannot be used."))
            # Tax-Free Threshold Constraints
            if rec.is_non_resident and rec.l10n_au_tax_free_threshold:
                raise ValidationError(_("A foreign resident cannot claim the tax-free threshold"))
            # Tax treatment category constraints
            if rec.l10n_au_tax_treatment_category == "V" and rec.l10n_au_income_stream_type != "VOL":
                raise ValidationError(_("Income Stream Type should be VOL for Tax Treatment Category V."))
            elif rec.l10n_au_tax_treatment_category == "H" and rec.l10n_au_income_stream_type != "WHM":
                raise ValidationError(_("Income Stream Type should be WHM for Tax Treatment Category H."))
            elif rec.l10n_au_tax_treatment_category == "C":
                if not (rec.l10n_au_tax_free_threshold or rec.is_non_resident):
                    raise ValidationError(_("Horticulturist must claim the Tax-free Threshold or be a Foreign Resident."))
            elif rec.l10n_au_tax_treatment_category == "W" and rec.l10n_au_income_stream_type != "SWP":
                raise ValidationError(_("Income Stream Type should be SWP for Tax Treatment Category W."))
            elif rec.l10n_au_tax_treatment_category == "S" and rec.is_non_resident:
                raise ValidationError(_("Seniors cannot be a foreign resident for tax purposes"))
            elif rec.l10n_au_tax_treatment_category == "F" and not rec.is_non_resident:
                raise ValidationError(_("Employees with Foreign Resident tax category must be a foreign resident for tax purposes."))

    @api.constrains(
        'l10n_au_tax_treatment_category',
        'l10n_au_tax_treatment_option_actor',
        'l10n_au_tax_treatment_option_voluntary',
        'l10n_au_tax_treatment_option_seniors',
        'l10n_au_employment_basis_code',
    )
    def _check_l10n_au_tax_treatment_option(self):
        for rec in self:
            if rec.l10n_au_tax_treatment_category == "V" and not rec.l10n_au_tax_treatment_option_voluntary:
                raise ValidationError(_("Voluntary Agreement Option is required for Tax Treatment Category Voluntary Agreement"))
            elif rec.l10n_au_tax_treatment_category == "S" and not rec.l10n_au_tax_treatment_option_seniors:
                raise ValidationError(_("Seniors Option is required for Tax Treatment Category Seniors & Pensioners"))
            if rec.l10n_au_employment_basis_code == "V" and rec.l10n_au_tax_treatment_category != "V":
                raise ValidationError(_("To use the Voluntary Employment Type you must be using the Voluntary Tax Treatment Category."))

    @api.constrains(
        "l10n_au_training_loan",
        "l10n_au_tax_treatment_category",
        "l10n_au_medicare_surcharge",
        "l10n_au_medicare_exemption",
        "l10n_au_medicare_reduction",
        "l10n_au_tfn_declaration",
        "l10n_au_tax_free_threshold")
    def _check_l10n_au_loan_and_medicare(self):
        for rec in self:
            if rec.l10n_au_medicare_surcharge != "X" and (rec.l10n_au_medicare_reduction != 'X' or rec.l10n_au_medicare_exemption != 'X'):
                raise ValidationError(_("Employees cannot claim both a surcharge and exemption/reduction for Medicare levy"))
            if rec.l10n_au_medicare_exemption == 'F' and rec.l10n_au_medicare_reduction != 'X':
                raise ValidationError(_("Medicare levy reduction is not possible if full exemption is claimed!"))
            if rec.l10n_au_medicare_reduction != 'X' and not rec.l10n_au_tax_free_threshold and rec.l10n_au_tfn_declaration != "000000000":
                raise ValidationError(_("Medicare levy reduction is only allowed for employees who have claimed tax-free threshold "
                    "and have not provided a TFN."))
            if rec.l10n_au_tax_treatment_category not in ["R", "S"]:
                if rec.l10n_au_tax_treatment_category != "F" and rec.l10n_au_training_loan:
                    raise ValidationError(_("Training loan is only available for Regular and Seniors & Pensioners and Foreign Residents"))
                if rec.l10n_au_medicare_surcharge != 'X' or rec.l10n_au_medicare_exemption != 'X' or rec.l10n_au_medicare_reduction != 'X':
                    raise ValidationError(_("Medicare surcharge, exemption and reduction are only available for Regular and Seniors & Pensioners"))

    @api.constrains('l10n_au_tfn')
    def _check_l10n_au_tfn(self):
        def validate_tfn(tfn):
            # Source: https://clearwater.com.au/code/tfn
            # Checksum
            weights = [1, 4, 3, 7, 5, 8, 6, 9, 10]
            tfn = re.sub(r'/[^\d]/', '', tfn)
            if len(tfn) == 9:
                sum = 0
                for i, t in enumerate(tfn):
                    sum += int(t) * weights[i]
                return sum % 11 == 0
            return False

        for employee in self:
            if employee.l10n_au_tfn_declaration != "provided":
                continue
            if employee.l10n_au_tfn and (len(employee.l10n_au_tfn) < 8 or not employee.l10n_au_tfn.isdigit()):
                raise ValidationError(_("The TFN must be at least 8 characters long and contain only numbers."))
            if employee.l10n_au_tfn and not validate_tfn(employee.l10n_au_tfn):
                raise ValidationError(_("The TFN %s is not valid. Please provide a valid TFN.", employee.l10n_au_tfn))

    # == Compute Methods ==

    @api.depends('l10n_au_tax_treatment_category')
    def _compute_l10n_au_income_stream_type(self):
        for rec in self:
            # rec.l10n_au_income_stream_type = "SAW"
            if rec.l10n_au_tax_treatment_category == "V":
                rec.l10n_au_income_stream_type = "VOL"
            elif rec.l10n_au_tax_treatment_category == "H":
                rec.l10n_au_income_stream_type = "WHM"
            elif rec.l10n_au_tax_treatment_category == "W":
                rec.l10n_au_income_stream_type = "SWP"
            else:
                rec.l10n_au_income_stream_type = rec.l10n_au_income_stream_type

    @api.depends(
        "l10n_au_tax_treatment_category",
        "l10n_au_employment_basis_code",
        "l10n_au_medicare_surcharge",
        "l10n_au_medicare_exemption",
        "l10n_au_medicare_reduction",
        "l10n_au_tax_free_threshold",
        "l10n_au_training_loan",
        "l10n_au_tfn_declaration",
        "is_non_resident",
        "l10n_au_tax_treatment_option_actor",
        "l10n_au_less_than_3_performance",
        "l10n_au_tax_treatment_option_voluntary",
        "l10n_au_tax_treatment_option_seniors",
        "company_id.l10n_au_registered_for_whm")
    def _compute_l10n_au_tax_treatment_code(self):
        for rec in self:
            code = rec.l10n_au_tax_treatment_category  # First character
            code += rec._get_second_code()  # Second Character
            # Third Character
            if rec.l10n_au_tax_treatment_category in ["R", "S", "F"] and rec.l10n_au_employment_basis_code != "D" and rec.l10n_au_training_loan:
                code += "S"
            else:
                code += "X"
            if rec.l10n_au_tax_treatment_category in ["R", "S"]:
                code += rec.l10n_au_medicare_surcharge  # Fourth Character
                code += rec.l10n_au_medicare_exemption  # Fifth Character
                code += rec.l10n_au_medicare_reduction  # Sixth Character
            else:
                code += 'XXX'
            rec.l10n_au_tax_treatment_code = code

    def _get_second_code(self) -> str:
        self.ensure_one()
        match self.l10n_au_tax_treatment_category:
            case "R":
                if self.l10n_au_employment_basis_code == "C":
                    code = "D"
                elif self.l10n_au_tax_free_threshold:
                    code = "T"
                else:
                    code = "N"
            case "A":
                if self.l10n_au_tax_treatment_option_actor == "P":
                    code = "P"
                # If actor option is Daily Performer
                elif not self.l10n_au_tax_free_threshold:
                    code = "N"
                else:
                    code = "D" if self.l10n_au_less_than_3_performance else "T"
            case "C":
                if self.is_non_resident:
                    code = "F"
                else:
                    code = "T"
            case "S":
                code = self.l10n_au_tax_treatment_option_seniors
                if self.l10n_au_tfn_declaration == "000000000":
                    code = "F"
            case "H":
                if self.l10n_au_tfn_declaration == "000000000":
                    code = "F"
                elif self.company_id.l10n_au_registered_for_whm:
                    code = "R"
                else:
                    code = "U"
            case "W":
                code = "P"
            case "F":
                code = "F"
            case "N":
                code = "F" if self.is_non_resident else "A"
            case "D":
                if self.l10n_au_employment_basis_code == "N":
                    code = "C"
                elif self.l10n_au_employment_basis_code == "D":
                    code = "B"
                else:
                    code = "V"
            case "V":
                code = self.l10n_au_tax_treatment_option_voluntary

        return str(code)

    @api.depends("l10n_au_tfn_declaration")
    def _compute_l10n_au_tfn(self):
        for employee in self:
            if employee.l10n_au_tfn_declaration != "provided":
                employee.l10n_au_tfn = employee.l10n_au_tfn_declaration
            else:
                employee.l10n_au_tfn = ""

    @api.depends("l10n_au_tfn", "l10n_au_income_stream_type")
    def _compute_l10n_au_abn(self):
        for employee in self:
            if employee.l10n_au_tfn and employee.l10n_au_income_stream_type != "VOL":
                employee.l10n_au_abn = ""

    def _inverse_l10n_au_abn(self):
        for employee in self:
            if employee.l10n_au_abn and employee.l10n_au_tfn_declaration != "000000000" and employee.l10n_au_income_stream_type != "VOL":
                employee.l10n_au_tfn = ""

    @api.depends("marital", "children", "l10n_au_tax_free_threshold")
    def _compute_l10n_au_medicare_reduction(self):
        for employee in self:
            employee.l10n_au_medicare_reduction = "X"
            if employee.marital in ["married", "cohabitant"] and employee.l10n_au_tax_free_threshold:
                if not employee.children:
                    employee.l10n_au_medicare_reduction = "0"
                elif employee.children < 10:
                    employee.l10n_au_medicare_reduction = str(employee.children)
                else:
                    employee.l10n_au_medicare_reduction = "A"

    def _get_active_super_accounts(self):
        """Get all available super accounts active during a payment cycle with some
        proportion assigned.

        Returns:
            l10n_au.super.account: Returns a Recordset of super accounts sorted by proportion
        """
        self.ensure_one()
        return self.l10n_au_super_account_ids\
            .filtered(lambda account: account.account_active and account.proportion > 0)\
            .sorted('proportion')

    @api.depends(
        "l10n_au_super_account_ids",
        "l10n_au_super_account_ids.proportion",
        "l10n_au_super_account_ids.account_active",
    )
    def _compute_proportion_warnings(self):
        proportions = self.env["l10n_au.super.account"].read_group(
            [("employee_id", "in", self.ids), ("account_active", "=", True)],
            ["proportion:sum"],
            ["employee_id"],
        )
        proportions = {p['employee_id'][0]: p['proportion'] for p in proportions}
        self.super_account_warning = False
        for emp in self:
            if proportions.get(emp.id) and float_compare(proportions.get(emp.id), 1, precision_digits=2) != 0:
                emp.super_account_warning = _(
                    "The proportions of super contributions for this employee do not amount to 100%% across their "
                    "active super accounts! Currently, it is at %d%%!",
                    proportions[emp.id] * 100,
                )
