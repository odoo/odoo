# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


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
        groups="hr.group_hr_user")
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
    l10n_au_scale = fields.Selection(
        selection=[
            ("1", "(1) National, tax-free threshold NOT claimed"),
            ("2", "(2) National, tax-free threshold claimed"),
            ("3", "(3) Foreign resident"),
            ("4", "(4) TFN not provided"),
            ("5", "(5) Medicare levy full exemption claimed"),
            ("6", "(6) Medicare levy half exemption claimed")],
        string="Scale For Withholding",
        compute="_compute_l10n_au_scale",
        inverse="_inverse_l10n_au_scale",
        store=True,
        required=True,
        readonly=False,
        default="4",
        groups="hr.group_hr_user")
    l10n_au_nat_3093_amount = fields.Float(
        string="Estimated Tax Offset",
        groups="hr.group_hr_user",
        help="Amount of tax offset the employee entered in his NAT3039 withholding declaration, 0 if the employee did not present a declaration")
    l10n_au_extra_pay = fields.Boolean(
        string="Withhold for Extra Pay",
        groups="hr.group_hr_user",
        help="Whether the employee wants additional withholding in case of 53 weekly pays or 27 fortnightly pays in a year")
    l10n_au_previous_id_bms = fields.Char(
        string="Previous BMS ID",
        groups="hr.group_hr_user")
    l10n_au_training_loan = fields.Boolean(
        string="HELP / STSL",
        compute="_compute_l10n_au_training_loan",
        store=True,
        readonly=False,
        groups="hr.group_hr_user",
        help="Whether the employee is a Study Training Support Loan (STSL) recipient")
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
    l10n_au_medicare_reduction = fields.Char(
        string="Medicare levy reduction",
        compute="_compute_l10n_au_medicare_reduction",
        store=True,
        groups="hr.group_hr_user",
        help="Medicare levy reduction, dependent on marital status and number of children")
    l10n_au_tax_free_threshold = fields.Boolean(
        string="Tax-free Threshold",
        groups="hr.group_hr_user")
    l10n_au_super_account_ids = fields.One2many(
        "l10n_au.super.account", "employee_id", string="Super Accounts")
    l10n_au_super_account_id = fields.Many2one(
        "l10n_au.super.account",
        string="Super Account",
        groups="hr.group_hr_user")
    l10n_au_child_support_deduction = fields.Float(
        string="Child Support Deduction",
        groups="hr.group_hr_user",
        help="Amount that has to be deducted every pay period, subject to Protected Earnings Amount (PEA)")
    l10n_au_child_support_garnishee = fields.Selection(
        selection=[
            ("fixed", "Fixed Amount"),
            ("percentage", "Percentage")],
        string="Child Support Garnishee",
        groups="hr.group_hr_user",
        help="""This amount is not subject to PEA and can be deducted in 3 different ways:
        as a fixed amount: same amount every pay period
        as a percentage: percentage of the employee's net pay
        as a lump sum: create a payslip input of type 'Child Support' instead""")
    l10n_au_child_support_garnishee_amount = fields.Float(
        string="Child Support Garnishee Amount",
        groups="hr.group_hr_user")

    @api.constrains('l10n_au_tfn')
    def _check_l10n_au_tfn(self):
        for employee in self:
            if employee.l10n_au_tfn and (len(employee.l10n_au_tfn) < 8 or not employee.l10n_au_tfn.isdigit()):
                raise ValidationError(_("The TFN must be at least 8 characters long and contain only numbers."))

    @api.depends("l10n_au_tfn_declaration")
    def _compute_l10n_au_tfn(self):
        for employee in self:
            if employee.l10n_au_tfn_declaration != "provided":
                employee.l10n_au_tfn = employee.l10n_au_tfn_declaration
            else:
                employee.l10n_au_tfn = ""

    @api.depends("l10n_au_tfn")
    def _compute_l10n_au_abn(self):
        for employee in self:
            if employee.l10n_au_tfn:
                employee.l10n_au_abn = ""

    def _inverse_l10n_au_abn(self):
        for employee in self:
            if employee.l10n_au_abn and employee.l10n_au_tfn_declaration == "provided":
                employee.l10n_au_tfn = ""

    @api.depends("is_non_resident", "l10n_au_tax_free_threshold", "l10n_au_tfn_declaration", "l10n_au_medicare_exemption")
    def _compute_l10n_au_scale(self):
        for employee in self:
            if employee.l10n_au_tfn_declaration == "000000000":
                employee.l10n_au_scale = "4"
            elif employee.is_non_resident:
                employee.l10n_au_scale = "3"
            elif employee.l10n_au_medicare_exemption == "F":
                employee.l10n_au_scale = "5"
            elif employee.l10n_au_medicare_exemption == "H":
                employee.l10n_au_scale = "6"
            elif employee.l10n_au_tax_free_threshold:
                employee.l10n_au_scale = "2"
            elif not employee.l10n_au_tax_free_threshold:
                employee.l10n_au_scale = "1"

    def _inverse_l10n_au_scale(self):
        for employee in self:
            employee.is_non_resident = employee.l10n_au_scale == "3"
            if employee.l10n_au_scale == "1":
                employee.l10n_au_tax_free_threshold = False
            elif employee.l10n_au_scale == "2":
                employee.l10n_au_tax_free_threshold = True
            elif employee.l10n_au_scale == "4":
                employee.l10n_au_tfn_declaration = "000000000"
            elif employee.l10n_au_scale == "5":
                employee.l10n_au_medicare_exemption = "F"
            elif employee.l10n_au_scale == "6":
                employee.l10n_au_medicare_exemption = "H"

    @api.depends("contract_id.l10n_au_tax_treatment_category")
    def _compute_l10n_au_training_loan(self):
        forbidden_categories = ["R", "A", "S", "F"]
        for employee in self:
            employee.l10n_au_training_loan = employee.contract_id.l10n_au_tax_treatment_category not in forbidden_categories

    @api.depends("marital", "children")
    def _compute_l10n_au_medicare_reduction(self):
        for employee in self:
            if employee.marital in ["married", "cohabitant"]:
                if not employee.children:
                    employee.l10n_au_medicare_reduction = "0"
                elif employee.children < 10:
                    employee.l10n_au_medicare_reduction = employee.children
                else:
                    employee.l10n_au_medicare_reduction = "A"
            else:
                employee.l10n_au_medicare_reduction = "X"

    def _l10n_au_get_super_account(self, date=fields.Date.today()):
        self.ensure_one()
        employee_accounts = self.l10n_au_super_account_ids.filtered(
            lambda account: account.date_from <= date).sorted('date_from')
        return employee_accounts[0] if employee_accounts else False
