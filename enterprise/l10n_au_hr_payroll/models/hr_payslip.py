# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from datetime import datetime, date
from math import floor, ceil
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools import groupby


PERIODS_PER_YEAR = {
    "daily": 260,
    "weekly": 52,
    "bi-weekly": 26,
    "semi-monthly": 24,
    "monthly": 12,
    "bi-monthly": 6,
    "quarterly": 4,
    "semi-annually": 2,
    "annually": 1,
}

NUMBER_OF_WEEKS = {
    "daily": 1 / 5,
    "weekly": 1,
    "bi-weekly": 2,
    "monthly": 13 / 3,
    "quarterly": 13,
    "annually": 13 * 4,
}


class HrPayslip(models.Model):
    _inherit = "hr.payslip"

    l10n_au_income_stream_type = fields.Selection(
        [
            ("SAW", "Salary and wages"),
            ("CHP", "Closely held payees"),
            ("IAA", "Inbound assignees to Australia"),
            ("WHM", "Working holiday makers"),
            ("SWP", "Seasonal worker programme"),
            ("FEI", "Foreign employment income"),
            ("JPD", "Joint petroleum development area"),
            ("VOL", "Voluntary agreement"),
            ("LAB", "Labour hire"),
            ("OSP", "Other specified payments"),
        ],
        compute="_compute_income_stream_type",
        store=True,
    )
    l10n_au_foreign_tax_withheld = fields.Float(
        string="Foreign Tax Withheld",
        help="Foreign tax withheld for the current financial year")
    l10n_au_exempt_foreign_income = fields.Float(
        string="Exempt Foreign Income",
        help="Exempt foreign income for the current financial year")
    l10n_au_schedule_pay = fields.Selection(related="contract_id.schedule_pay", store=True, index=True)
    l10n_au_termination_type = fields.Selection([
        ("normal", "Non-Genuine Redundancy"),
        ("genuine", "Genuine Redundancy"),
    ], string="Termination Type", readonly=True)
    l10n_au_extra_negotiated_super = fields.Float(compute="_compute_l10n_au_extra_negotiated_super", store=True, readonly=True)
    l10n_au_extra_compulsory_super = fields.Float(compute="_compute_l10n_au_extra_compulsory_super", store=True, readonly=True)
    l10n_au_salary_sacrifice_superannuation = fields.Float(compute="_compute_l10n_au_salary_sacrifice_superannuation", store=True, readonly=True)
    l10n_au_salary_sacrifice_other = fields.Float(compute="_compute_l10n_au_salary_sacrifice_other", store=True, readonly=True)
    payslip_ytd_totals = fields.Json(compute="_compute_payslip_ytd_totals")

    def _get_data_files_to_update(self):
        # Note: file order should be maintained
        return super()._get_data_files_to_update() + [(
            'l10n_au_hr_payroll', [
                'data/hr_payslip_input_type_data.xml',
                'data/salary_rules/hr_salary_rule_regular_data.xml',
                'data/hr_rule_parameters_data.xml',
            ])]

    def _get_base_local_dict(self):
        res = super()._get_base_local_dict()
        if self.country_code != "AU":
            return res
        slips = self._l10n_au_get_year_to_date_slips()
        res.update({
            "year_slips": slips,
            "ytd_total": self._l10n_au_get_year_to_date_totals(),
            "ytd_gross": slips._get_line_values(['GROSS'], compute_sum=True)['GROSS']['sum']['total'],
            "ytd_inputs": self._l10n_au_get_ytd_inputs(),
        })
        return res

    def _get_daily_wage(self):
        schedule_pay = self.contract_id.schedule_pay
        wage = self.contract_id.wage
        if self.contract_id.wage_type == 'hourly':
            wage *= (1 + self.contract_id.l10n_au_casual_loading)

        if schedule_pay == "daily":
            return wage
        elif schedule_pay == "weekly":
            return wage / 5
        elif schedule_pay == "bi-weekly":
            return wage / 10
        elif schedule_pay == "monthly":
            return wage * 3 / 13 / 5
        elif schedule_pay == "quarterly":
            return wage / 13 / 5
        else:
            return wage

    def _compute_input_line_ids(self):
        super()._compute_input_line_ids()
        for payslip in self:
            if not payslip.struct_id or payslip.company_id.country_id.code != "AU":
                continue
            # this only works if the payslip is saved after struct type is changed, because it depends on the structure
            # type that was selected before.
            new_types = payslip.struct_id.type_id.l10n_au_default_input_type_ids
            # Remove the lines not default for new structure and keep user defined allowances
            to_remove_lines = payslip.input_line_ids.filtered(lambda i: i.input_type_id not in new_types and i.l10n_au_is_default_allowance)
            to_remove_vals = [(2, line.id) for line in to_remove_lines]
            to_add_vals = []
            # Add default lines not already on the payslip
            for default_allowance in new_types.filtered(lambda x: x not in payslip.input_line_ids.input_type_id):
                to_add_vals.append((0, 0, {
                    'amount': default_allowance.l10n_au_default_amount,
                    'input_type_id': default_allowance.id,
                    'l10n_au_is_default_allowance': True,
                }))
            input_line_vals = to_remove_vals + to_add_vals
            payslip.update({'input_line_ids': input_line_vals})
            # automatic description for other types
            for line in payslip.input_line_ids.filtered(lambda line: line.code == "OD"):
                line.name = line.input_type_id.name.split("-")[1].strip()

    # Computed here to keep individual values for each payslip without a separate salary rule
    # Only recompute when payslip is recomputed or when contract is changed
    @api.depends('contract_id')
    def _compute_l10n_au_extra_negotiated_super(self):
        for payslip in self:
            if payslip.country_code != "AU":
                continue
            if payslip.state not in ['draft', 'verify']:
                continue
            payslip.l10n_au_extra_negotiated_super = payslip.contract_id.l10n_au_extra_negotiated_super

    @api.depends('contract_id')
    def _compute_l10n_au_extra_compulsory_super(self):
        for payslip in self:
            if payslip.country_code != "AU":
                continue
            if payslip.state not in ['draft', 'verify']:
                continue
            payslip.l10n_au_extra_compulsory_super = payslip.contract_id.l10n_au_extra_compulsory_super

    @api.depends('contract_id')
    def _compute_l10n_au_salary_sacrifice_superannuation(self):
        for payslip in self:
            if payslip.country_code != "AU":
                continue
            if payslip.state not in ['draft', 'verify']:
                continue
            payslip.l10n_au_salary_sacrifice_superannuation = payslip.contract_id.l10n_au_salary_sacrifice_superannuation

    @api.depends('contract_id')
    def _compute_l10n_au_salary_sacrifice_other(self):
        for payslip in self:
            if payslip.country_code != "AU":
                continue
            if payslip.state not in ['draft', 'verify']:
                continue
            payslip.l10n_au_salary_sacrifice_other = payslip.contract_id.l10n_au_salary_sacrifice_other

    @api.depends("employee_id")
    def _compute_income_stream_type(self):
        for payslip in self:
            payslip.l10n_au_income_stream_type = payslip.employee_id.l10n_au_income_stream_type

    @api.model
    def _template_payslip_ytd_totals(self, with_inputs=False):
        return {
            "slip_lines": defaultdict(lambda: defaultdict(float)),
            "worked_days": defaultdict(lambda: {"amount": 0.0, "is_leave": False, "payroll_code": False}),
            "periods": 0,
            "fields": defaultdict(float),
            "input_lines": defaultdict(lambda: {
                    "amount": 0.0, "code": "", "payroll_code": "", "payment_type": "", "payroll_code_description": "",
                }) if with_inputs else {},
        }

    @api.model
    def _clean_payslip_ytd_totals(self, totals):
        """ Json converts integer keys to string and drops 'defaultdict'.
            This method converts the keys back to integer and adds the 'defaultdict'.
        """
        if not totals:
            return {}
        clean_totals = {}
        for income_stream, income_stream_totals in totals.items():
            clean_totals[income_stream] = self._template_payslip_ytd_totals(with_inputs=True)
            for category, categ_values in income_stream_totals["slip_lines"].items():
                for code, value in categ_values.items():
                    if value:
                        clean_totals[income_stream]["slip_lines"][category][code] = value
            for entry_type, values in income_stream_totals["worked_days"].items():
                if values["amount"]:
                    clean_totals[income_stream]["worked_days"][int(entry_type)] = values
            clean_totals[income_stream]["periods"] = income_stream_totals["periods"]
            for field, value in income_stream_totals["fields"].items():
                clean_totals[income_stream]["fields"][field] = value
            for input_type, values in income_stream_totals["input_lines"].items():
                if values["amount"]:
                    clean_totals[income_stream]["input_lines"][int(input_type)] = values
        return clean_totals

    @api.depends_context("l10n_au_include_current_slip")
    @api.depends("employee_id", "employee_id.slip_ids", "date_from", "date_to", "state", "line_ids", "input_line_ids")
    def _compute_payslip_ytd_totals(self):
        """ Dict with all the year to date totals for the payslip.
        Each slip has the YTD computed based on all the previous slips. These are grouped
        by income stream type.

        Force include current slip using `l10n_au_include_current_slip`
        Not stored to allow recomputing if a new slip is added to a previous period.

        Example: (All slips from same employee)
        Slip 1: ytd = Slip 1
        Slip 2: ytd = Slip 1 + Slip 2
        Slip 3: ytd = Slip 1 + Slip 2 + Slip 3
        """
        self.update({"payslip_ytd_totals": {}})
        au_slips = self.filtered(lambda x: x.country_code == "AU")
        if not au_slips:
            return
        # Groups the ytd slips for each payslip
        slips_to_read = self.browse()
        ytd_slips = defaultdict(lambda: self.env["hr.payslip"])
        for slip in au_slips:
            ytd_slips[slip.id] = slip._l10n_au_get_year_to_date_slips(l10n_au_include_current_slip=self.env.context.get("l10n_au_include_current_slip"))
            slips_to_read |= ytd_slips[slip.id]

        fields_to_compute = [
            "l10n_au_foreign_tax_withheld",
            "l10n_au_exempt_foreign_income",
            "l10n_au_salary_sacrifice_other",
            "l10n_au_salary_sacrifice_superannuation",
            "l10n_au_extra_negotiated_super",
            "l10n_au_extra_compulsory_super",
        ]
        # Prefetch the data to avoid multiple reads
        slips_to_read.fetch(fields_to_compute + ["l10n_au_income_stream_type"])
        slip_lines_data = self.env["hr.payslip.line"].search_fetch(
            [("slip_id", "in", slips_to_read.ids)],
            ["slip_id", "category_id", "code", "total"],
        )
        worked_days_data = self.env["hr.payslip.worked_days"].search_fetch(
            [("payslip_id", "in", slips_to_read.ids)],
            ["payslip_id", "code", "amount", "work_entry_type_id"],
        )
        input_lines_data = self.env["hr.payslip.input"].search_fetch(
            [("payslip_id", "in", slips_to_read.ids)],
            ["payslip_id", "code", "amount", "l10n_au_payroll_code_description", "l10n_au_payroll_code", "l10n_au_payment_type"],
        )
        lump_sum_e = self.env.ref("l10n_au_hr_payroll.l10n_au_lumpsum_e")

        for payslip in au_slips.sorted(key=lambda x: x.date_from):
            year_slips = ytd_slips[payslip.id]
            totals = {
                income_stream: self._template_payslip_ytd_totals(with_inputs=True)
                for income_stream in set((year_slips + payslip).mapped("l10n_au_income_stream_type"))
            }

            for line in slip_lines_data.filtered(lambda x: x.slip_id.id in year_slips.ids):
                totals[line.slip_id.l10n_au_income_stream_type]["slip_lines"][line.category_id.code][line.code] += line.total
                totals[line.slip_id.l10n_au_income_stream_type]["slip_lines"][line.category_id.code]["total"] += line.total

            for line in worked_days_data.filtered(lambda x: x.payslip_id.id in year_slips.ids):
                totals[line.payslip_id.l10n_au_income_stream_type]["worked_days"][line.work_entry_type_id.id]["amount"] += line.amount
                totals[line.payslip_id.l10n_au_income_stream_type]["worked_days"][line.work_entry_type_id.id]["is_leave"] = line.work_entry_type_id.is_leave
                totals[line.payslip_id.l10n_au_income_stream_type]["worked_days"][line.work_entry_type_id.id]["payroll_code"] = line.work_entry_type_id.l10n_au_work_stp_code

            for income_stream, slips in groupby(year_slips, lambda x: x.l10n_au_income_stream_type):
                for field in fields_to_compute:
                    totals[income_stream]["fields"][field] = sum(slip[field] for slip in slips)

            for input_line in input_lines_data.filtered(lambda x: x.payslip_id.id in year_slips.ids):
                if input_line.input_type_id.id not in totals[input_line.payslip_id.l10n_au_income_stream_type]["input_lines"]:
                    totals[input_line.payslip_id.l10n_au_income_stream_type]["input_lines"][input_line.input_type_id.id] = {
                        "amount": 0.0,
                        "code": input_line.code,
                        "payroll_code": input_line.l10n_au_payroll_code,
                        "payment_type": input_line.l10n_au_payment_type,
                        "payroll_code_description": input_line.l10n_au_payroll_code_description,
                    }
                if input_line.input_type_id == lump_sum_e:
                    totals[input_line.payslip_id.l10n_au_income_stream_type]["input_lines"][input_line.input_type_id.id]["financial_year"] = input_line.name
                totals[input_line.payslip_id.l10n_au_income_stream_type]["input_lines"][input_line.input_type_id.id]["amount"] += input_line.amount
            payslip.payslip_ytd_totals = totals

    @api.constrains('input_line_ids', 'employee_id')
    def _check_input_lines(self):
        for payslip in self:
            employee = payslip.employee_id
            input_director_fees = self.env.ref("l10n_au_hr_payroll.input_gross_director_fee")
            if input_director_fees in payslip.input_line_ids.mapped("input_type_id") \
                and employee.l10n_au_income_stream_type in ["OSP", "WHM", "LAB", "VOL", "SWP"]:
                raise ValidationError(_(
                    "Director fees are not allowed for income stream type '%s'.",
                    employee.l10n_au_income_stream_type,
                ))

            if (payslip.contract_id.l10n_au_salary_sacrifice_superannuation or payslip.contract_id.l10n_au_salary_sacrifice_other)\
                and employee.l10n_au_income_stream_type in ["OSP", "LAB", "VOL"]:
                raise ValidationError(_(
                    "Salary sacrifice is not allowed for income stream type '%s'.",
                    self.employee_id.l10n_au_income_stream_type,
                ))

            if payslip.input_line_ids.filtered(lambda x: x.code == "BACKPAY.INPUT") and employee.l10n_au_income_stream_type == "OSP":
                raise ValidationError(_("Bonuses and Commissions are not allowed for income stream type 'OSP'."))

            overtime_lines = payslip.worked_days_line_ids.filtered(lambda l: l.work_entry_type_id.l10n_au_work_stp_code == "T")
            overtime_inputs = payslip.input_line_ids.filtered(lambda l: l.l10n_au_payroll_code == "Overtime")
            if (overtime_lines or overtime_inputs) and employee.l10n_au_income_stream_type in ["OSP", "LAB", "VOL"]:
                raise ValidationError(_("Overtime is not allowed for income stream type '%s'.", employee.l10n_au_income_stream_type))

            if payslip.l10n_au_foreign_tax_withheld and employee.l10n_au_income_stream_type != "FEI":
                raise ValidationError(_("Foreign Income tax Witholding is only allowed for income stream type 'FEI'."))
            if payslip.l10n_au_exempt_foreign_income and employee.l10n_au_income_stream_type != "SAW":
                raise ValidationError(_("Exempt Foreign Income is only allowed for income stream type 'SAW'."))

    @api.model_create_multi
    def create(self, vals_list):
        payslips = super().create(vals_list)
        payslips._add_unused_leaves_to_payslip()
        return payslips

    def compute_sheet(self):
        # Update the contribution amounts from the contract
        self.env.add_to_compute(self._fields['l10n_au_extra_negotiated_super'], self)
        self.env.add_to_compute(self._fields['l10n_au_extra_compulsory_super'], self)
        self.env.add_to_compute(self._fields['l10n_au_salary_sacrifice_superannuation'], self)
        self.env.add_to_compute(self._fields['l10n_au_salary_sacrifice_other'], self)
        return super().compute_sheet()

    def action_refresh_from_work_entries(self):
        # Force Recompute gross unused leaves amounts
        self.sudo()._add_unused_leaves_to_payslip()
        super().action_refresh_from_work_entries()

    def action_payslip_done(self):
        lump_sum_e = self.env.ref("l10n_au_hr_payroll.l10n_au_lumpsum_e")
        for line in self.input_line_ids:
            if line.input_type_id == lump_sum_e:
                if not line.name.isnumeric() or len(line.name) != 4:
                    raise UserError(_(
                        "Invalid Financial year on Payslip %s. The description of input Lump Sum E should be the financial year.",
                        self.name
                    ))
        super().action_payslip_done()

    def _l10n_au_get_year_to_date_slips(self, l10n_au_include_current_slip=False):
        """ Returns a list of all payslips in the same fiscal year as the current payslip.
            Current slip is included if it is done. Else it can be forced to be included using
            'l10n_au_include_current_slip=True'
        """
        start_year = self.contract_id._l10n_au_get_financial_year_start(self.date_from)
        year_slips = self.env["hr.payslip"].search([
            ("employee_id", "=", self.employee_id.id),
            ("company_id", "=", self.company_id.id),
            ("state", "in", ["paid", "done"]),
            ("date_from", ">=", start_year),
            ("date_from", "<=", self.date_from),
        ], order="date_from")
        # To include the current slip while its not done
        if l10n_au_include_current_slip:
            year_slips |= self
        return year_slips

    def _l10n_au_get_year_to_date_totals(self, fields_to_compute=None, l10n_au_include_current_slip=False):
        """ Uses the 'payslip_ytd_totals' field to return YTD values. Can be computed once and manipulated
            to get the desired values according to the arguments.
        """
        fields_to_compute = fields_to_compute or []
        # Add as a method arg in master
        group_income_stream_types = self.env.context.get("group_income_stream_types", False)
        payslip_ytd_totals = self.with_context(l10n_au_include_current_slip=l10n_au_include_current_slip).payslip_ytd_totals
        payslip_ytd_totals = self._clean_payslip_ytd_totals(payslip_ytd_totals)

        if group_income_stream_types:
            totals = payslip_ytd_totals
        else:
            # Sum all income stream types from payslip_ytd_totals
            totals = self._template_payslip_ytd_totals()
            for income_stream, income_stream_totals in payslip_ytd_totals.items():
                for category, slip_line in income_stream_totals["slip_lines"].items():
                    for code, value in slip_line.items():
                        totals["slip_lines"][category][code] += value
                for entry_type, worked_day_total in income_stream_totals["worked_days"].items():
                    totals["worked_days"][entry_type]["amount"] += worked_day_total["amount"]
                    totals["worked_days"][entry_type]["is_leave"] = worked_day_total["is_leave"]
                    totals["worked_days"][entry_type]["payroll_code"] = worked_day_total["payroll_code"]
                totals["periods"] += income_stream_totals["periods"]
                for field, value in income_stream_totals["fields"].items():
                    totals["fields"][field] += value
                    if field in fields_to_compute:
                        fields_to_compute.remove(field)

        # Add any remaining fields to compute
        if fields_to_compute:
            year_slips = self._l10n_au_get_year_to_date_slips(l10n_au_include_current_slip=l10n_au_include_current_slip)
            for income_stream, slips in groupby(year_slips, lambda x: x.l10n_au_income_stream_type):
                for field in fields_to_compute:
                    if group_income_stream_types:
                        totals[income_stream]["fields"][field] = sum(slip[field] for slip in slips)
                    else:
                        totals["fields"][field] += sum(slip[field] for slip in slips)

        return totals

    def _l10n_au_get_ytd_inputs(self, l10n_au_include_current_slip=False):
        payslip_ytd_totals = self.with_context(l10n_au_include_current_slip=l10n_au_include_current_slip).payslip_ytd_totals
        payslip_ytd_totals = self._clean_payslip_ytd_totals(payslip_ytd_totals)
        group_income_stream_types = self.env.context.get("group_income_stream_types", False)
        if group_income_stream_types:
            input_totals = {}
            for income_stream, income_stream_totals in payslip_ytd_totals.items():
                input_totals[income_stream] = income_stream_totals["input_lines"]
        else:
            input_totals = self._template_payslip_ytd_totals(with_inputs=True)["input_lines"]
            for income_stream, income_stream_totals in payslip_ytd_totals.items():
                for input_type, input_line in income_stream_totals["input_lines"].items():
                    if input_type not in input_totals:
                        input_totals[input_type] = input_line
                    else:
                        input_totals[input_type]["amount"] += input_line["amount"]
        return input_totals

    @api.model
    def _l10n_au_compute_weekly_earning(self, amount, period):
        """ Given an amount and a pay schedule, calculate the weekly earning used to calculate withholding amounts.
        The amount given should already include any allowances that are subject to withholding.

        The calculation, recommended by the legislation, is as follows:

        Example:
            Weekly income                           $ 467.59
            Add allowance subject to withholding    $ 9.50
            Total earnings (ignore cents)           $ 477.00
            Add 99 cents                            $ 0.99
          Weekly earnings                           $ 477.99

        If the period is other than weekly, for withholding purposes, we should calculate the equivalent weekly earnings
        and use it for the computation.

        :param amount: The amount paid in the period.
        :param period: The pay schedule in use (weekly, fortnightly or monthly)
        :return: the weekly earnings subject to withholding
        """
        if period == "monthly" and round(amount % 1, 2) == 0.33:
            amount += 0.01
        weekly_amount = self._l10n_au_convert_amount(amount, period, "weekly")
        return floor(weekly_amount) + 0.99

    @api.model
    def _l10n_au_convert_amount(self, amount, period_from, period_to):
        """
        Convert an amount from a period to another.
        https://www.ato.gov.au/tax-rates-and-codes/payg-withholding-schedule-1-statement-of-formulas-for-calculating-amounts-to-be-withheld/working-out-the-weekly-earnings
        """
        if period_to == "weekly":
            return amount / NUMBER_OF_WEEKS[period_from]
        coefficient = PERIODS_PER_YEAR[period_from] / PERIODS_PER_YEAR[period_to]
        return amount * coefficient

    def _l10n_au_compute_withholding_amount(self, period_earning, period, coefficients, unused_leaves=False):
        """
        Compute the withholding amount for the given period.

        :param period_earning: The gross earning (after allowances subjects to withholding)
        :param period: The type of pay schedule (weekly, fortnightly, or monthly)
        :param coefficients: The scale that should be applied to this employee. It will depend on their schedule.
        """
        self.ensure_one()
        employee_id = self.employee_id
        # if custom withholding rate
        if employee_id.l10n_au_withholding_variation != "none" and not unused_leaves\
            or employee_id.l10n_au_withholding_variation == "leaves":
            return period_earning * employee_id.l10n_au_withholding_variation_amount / 100

        # Compute the weekly earning as per government legislation.
        # They recommend to calculate the weekly equivalent of the earning, if using another pay schedule.
        # https://www.ato.gov.au/tax-rates-and-codes/payg-withholding-schedule-1-statement-of-formulas-for-calculating-amounts-to-be-withheld/using-a-formula?anchor=Usingaformula#Usingaformula
        weekly_earning = self._l10n_au_compute_weekly_earning(period_earning, period)
        weekly_withhold = 0.0

        # For scale 4 (no tfn provided), cents are ignored when applying the rate.
        # Final withhold amount is rounded up
        if (employee_id.l10n_au_tax_treatment_category == "N"
            or employee_id.l10n_au_tfn_declaration == '000000000'):
            weekly_withhold = floor(weekly_earning) * (coefficients / 100)
            return ceil(self._l10n_au_convert_amount(weekly_withhold, "weekly", period))

        # Categories with flat rate withholding
        if (
            employee_id.l10n_au_tax_treatment_category in ["C", "V"]
            or (
                employee_id.l10n_au_tax_treatment_category == "W"
                and self.company_id.l10n_au_registered_for_palm
            )
            or (
                employee_id.l10n_au_tax_treatment_category == "A"
                and employee_id.l10n_au_tax_treatment_option_actor == "P"
            )
        ):
            weekly_withhold = weekly_earning * (coefficients / 100)
            return self._l10n_au_convert_amount(weekly_withhold, "weekly", period)
        # The formula to compute the withholding amount is:
        #   y = a * x - b, where:
        #   y is the weekly amount to withhold
        #   x is the number of whole dollars in the weekly earning + 99 cents
        #   a and b are the coefficient defined in the data.
        for coef in coefficients:
            if weekly_earning < float(coef[0]):
                weekly_withhold = coef[1] * weekly_earning - coef[2]
                break

        amount = round(weekly_withhold)
        period_amount = self._l10n_au_convert_amount(amount, "weekly", period)
        if period in ["daily", "monthly"]:
            period_amount = round(period_amount)
        return period_amount

    def _l10n_au_compute_medicare_adjustment(self, period_earning, period, params: dict):
        """ Compute the Medicare adjustment for the given period.
        Medicare has 3 components:
            - Medicare Levy Exemption: This can be half or full exemption. The standard rate is 2% 'ML' key in rule params.
                This is positive amount that reduces total withhold.
            - Medicare Levy Reduction: This is a reduction in the Medicare levy based on the family situation. This reduces
                the total withhold.
            - Medicare Levy Surcharge: This is a surcharge for high-income earners without private health insurance. This
                increases the total withhold.
        """
        self.ensure_one()
        # Medicare Exemption
        exemption = 0
        if self.employee_id.l10n_au_medicare_exemption != "X":
            exemption = period_earning * params["ML"]

        # Medicare Surcharge
        surcharge = 0
        if self.employee_id.l10n_au_medicare_surcharge != "X":
            rate = {"1": 0.01, "2": 0.0125, "3": 0.015}
            surcharge = period_earning * rate[self.employee_id.l10n_au_medicare_surcharge]

        # Medicare reduction
        adjustment = 0
        if self.employee_id.l10n_au_tax_free_threshold and self.employee_id.l10n_au_medicare_reduction != "X":
            weekly_earning = self._l10n_au_compute_weekly_earning(period_earning, period)
            child_reduction = params["ADDC"] * int(self.employee_id.l10n_au_medicare_reduction)
            weekly_family_threshold = (child_reduction + self.contract_id.l10n_au_yearly_wage) / 52

            shading_out_point = floor(weekly_family_threshold * params["SOPD"] / params["SOPM"])
            weekly_levy_adjustment = 0
            if weekly_earning < params["WEST"]:
                weekly_levy_adjustment = (weekly_earning - params["WLA"]) * params["SOPM"]
            elif weekly_earning >= params["WEST"] and weekly_earning < weekly_family_threshold:
                weekly_levy_adjustment = weekly_earning * params["ML"]
            elif weekly_earning >= weekly_family_threshold and weekly_earning < shading_out_point:
                weekly_levy_adjustment = (weekly_family_threshold * params["ML"]) - ((weekly_earning - weekly_family_threshold) * params["SOPD"])
            amount = round(weekly_levy_adjustment)
            adjustment = self._l10n_au_convert_amount(amount, "weekly", period)
            if period in ["daily", "monthly"]:
                adjustment = round(adjustment)

        return adjustment + exemption - surcharge

    def _l10n_au_compute_lumpsum_withhold(self, lumpsum):
        '''
        Withholding for back payments is calculated by apportioning it over the number of periods it applies for and
        summing the difference in withholding over every period.
        '''
        self.ensure_one()
        return lumpsum * 0.47

    def _l10n_au_compute_loan_withhold(self, period_earning, period, coefficients):
        self.ensure_one()
        # STSL withholding from 24 sept 2025 onwards to use schedule 1 formula
        # https://softwaredevelopers.ato.gov.au/2025-pay-you-go-payg-withholding-tax-tables
        if self.date_from >= date(2025, 9, 24):
            return self._l10n_au_compute_withholding_amount(period_earning, period, coefficients)

        weekly_earning = self._l10n_au_compute_weekly_earning(period_earning, period)
        weekly_withhold = 0.0
        if weekly_earning <= coefficients[0][1]:
            return 0.0

        for coef in coefficients:
            if coef[1] == "inf" or weekly_earning <= coef[1]:
                weekly_withhold = coef[2] / 100 * weekly_earning
                break

        amount = round(weekly_withhold)
        period_amount = self._l10n_au_convert_amount(amount, "weekly", period)
        if period in ["daily", "monthly"]:
            period_amount = round(period_amount)

        return period_amount

    @api.model
    def _l10n_au_get_tax_free_etp_types(self):
        return self.env["hr.payslip.input.type"].concat(
            self.env.ref("l10n_au_hr_payroll.input_genuine_redundancy"),
            self.env.ref("l10n_au_hr_payroll.input_early_retirement_scheme"),
            self.env.ref("l10n_au_hr_payroll.input_in_lieu_of_notice_genuine"),
            self.env.ref("l10n_au_hr_payroll.input_severance_pay_genuine"),
        )

    def _l10n_au_compute_termination_withhold(self, ytd_total):
        """
        Compute the withholding amount for the termination payment.

        It is done in x steps:
            - We first work out the smallest cap that will apply to this withholding computation
            - We use this cap to work out the withholding amount

        Currently missing feature in the computation:
            - Multiple payments for a single termination. This could happen and will affect the cap.
            - Death benefits. The withholding amount is impacted by a number of factor, like the beneficiary of the payment.
            - Foreign residents tax treaties, which should exempt a foreign resident from a country with a treaty from the withholding tax.
            - Tax free component.
                An ETP has a tax-free component if part of the payment relate to invalidity or employment before 1 July 1983
            - Handling delayed withholding.

        The withholding amount is rounded up to the nearest dollar.
        If no TFN is provided, the cents are ignored when calculating the withholding amount.
        """
        self.ensure_one()

        # 1) Working out the smallest cap.
        # ================================
        # We first calculate the whole-of-income cap by subtracting the sum of taxable payments made to the employee from $180000
        # We then compare the whole-of-income cap with the ETP cap amount. This amount changes every year.
        # If both caps are equal, we use the whole-of-income cap. Otherwise, we use the smallest of the two caps.

        whole_of_income_cap = (self._rule_parameter("l10n_au_whoic_cap_schedule_11")
                               - ytd_total["slip_lines"]["GROSS"]["total"])
        etp_cap = self._rule_parameter("l10n_au_etp_cap_schedule_11")
        smallest_withholding_cap = min(whole_of_income_cap, etp_cap)

        # 2) Working out the withholding amount
        # =====================================
        # An ETP can be made up of a tax-free component and a taxable component from which we much withheld an amount.
        # The tax-free component is exempt from any withholding.

        # The withheld will be different if the employee as given its TFN to the employer.
        # In this case, we apply the amount calculated by applying the table rounded up to the nearest dollar.

        # For a foreign resident, it will depend on whether there is a tax treaty with their country of residence.
        # If the ETP is only assessable in the other country, no withholding is required.
        # It the ETP is assessable in Australia, the withholding is using the same table but requires to exclude the Medicare levy of 2%

        # When a TFN has not been provided, you must withhold 47% to a resident and 45% to a foreign resident.
        # =====================================

        # a) Compute the preservation age.
        # The withholding amount varies depending on whether the employee has reached their preservation age by the
        # end of the income year in which the payment is made.
        employee_id = self.employee_id
        if not employee_id.birthday:
            raise UserError(_("In order to process a termination payment, a birth date should be set on the private information tab of the employee's form view."))

        tfn_provided = employee_id.l10n_au_tfn_declaration != "000000000"
        is_non_resident = employee_id.is_non_resident
        life_benefits_etp_rates = self._rule_parameter("l10n_au_etp_withholding_life_benefits_schedule_11")
        over_the_cap_rate = life_benefits_etp_rates['over_cap']
        no_tfn_rate = life_benefits_etp_rates['no_tfn']

        # These payments are subjects to a tax-free limit.
        tax_free_types = self._l10n_au_get_tax_free_etp_types()

        preservation_ages = self._rule_parameter("l10n_au_preservation_age_schedule_11")
        # The preservation age is determined based on the financial year in which the employee was born.
        birth_financial_year = self.contract_id._l10n_au_get_financial_year_start(employee_id.birthday).year
        years_list = list(preservation_ages['years'].values())
        if birth_financial_year < years_list[0]:
            preservation_age = preservation_ages['before']
        elif birth_financial_year > years_list[-1]:
            preservation_age = preservation_ages['after']
        else:
            preservation_age = preservation_ages['years'][str(birth_financial_year)]

        is_of_or_over_preservation_age = relativedelta(date.today(), employee_id.birthday).years >= preservation_age

        # b) Some payments have a tax free limit, which depends on the completed years of services.
        complete_years_of_service = relativedelta(self.date_to, employee_id.first_contract_date).years
        base_tax_free_limit = self._rule_parameter("l10n_au_tax_free_base_schedule_11")
        tax_free_limit = base_tax_free_limit + (complete_years_of_service * self._rule_parameter("l10n_au_tax_free_yearly_schedule_11"))

        # c) tax-free component.
        tax_free_amount = 0.0

        # d) Compute the withholding.
        withholding_amount = 0.0
        # We need to always deal with the payment subject to the ETP cap first.
        for input_line in self.input_line_ids.sorted(key=lambda i: 0 if i.input_type_id.l10n_au_etp_type == 'excluded' else 1):
            if input_line.input_type_id.l10n_au_payment_type != 'etp':
                continue
            taxable_amount = input_line.amount
            applicable_tax_free_limit = 0
            # We check if the payment is subject to a tax-free limit.
            if input_line.input_type_id in tax_free_types:
                applicable_tax_free_limit = tax_free_limit

            tax_free_amount += min(applicable_tax_free_limit, input_line.amount)
            taxable_amount = max(0, taxable_amount - applicable_tax_free_limit)
            # Besides that, the remaining taxable amounts are all subjects to withholding.
            # If no tfn has been provided, the rate will be fixed to 47% (for residents) or 45% (for non-residents)
            if not tfn_provided:
                applicable_rate = no_tfn_rate
            else:
                age_group = 'over' if is_of_or_over_preservation_age else 'under'
                applicable_rate = life_benefits_etp_rates[input_line.input_type_id.l10n_au_etp_type][age_group]

            # If a foreign resident's ETP is assessable in Australia, Adjust the rate to exclude the Medicare levy of 2%.
            if is_non_resident:
                applicable_rate -= 2
            # Depending on the type of payment, we either use the ETP cap, or the smallest ETP cap computed earlier.
            applicable_cap = etp_cap if input_line.input_type_id.l10n_au_etp_type == 'excluded' else smallest_withholding_cap
            # Separate between the amount below the cap, and the amount above the cap (if any)
            taxable_amount_under_cap = min(applicable_cap, taxable_amount)
            taxable_amount_over_cap = taxable_amount - taxable_amount_under_cap
            # Then apply the rates accordingly.
            if tfn_provided:
                withholding_amount += taxable_amount_under_cap * (applicable_rate / 100)
                withholding_amount += taxable_amount_over_cap * (over_the_cap_rate / 100)
            else:  # When no tfn is provided, ignore the cents when computing the withholding amount.
                withholding_amount += int(taxable_amount_under_cap * (applicable_rate / 100))
                withholding_amount += int(taxable_amount_over_cap * (over_the_cap_rate / 100))
            etp_cap -= taxable_amount

        return round(withholding_amount), tax_free_amount

    def _l10n_au_get_unused_leave_by_type(self):
        """ Returns the amount of unused leaves by type and totals of each type
        """
        cutoff_dates = [datetime(1978, 8, 16).date(), datetime(1993, 8, 17).date()]
        leaves_by_date = defaultdict(lambda:
            {
                "annual": {
                    "pre_1978": 0.0,
                    "pre_1993": 0.0,
                    "post_1993": 0.0,
                },
                "long_service": {
                    "pre_1978": 0.0,
                    "pre_1993": 0.0,
                    "post_1993": 0.0,
                },
            }
        )
        allocations = self.env["hr.leave.allocation"].search([
            ("state", "=", "validate"),
            ("holiday_status_id.l10n_au_leave_type", "in", ['annual', 'long_service']),
            ("employee_id", "in", self.employee_id.ids),
        ])
        for payslip in self:
            for allocation in allocations.filtered(
                lambda x:
                    x.employee_id == self.employee_id and
                    x.date_from <= (payslip.contract_id.date_end or payslip.date_to)
                ):
                leave_type = leaves_by_date[payslip.id][allocation.holiday_status_id.l10n_au_leave_type]
                unused = allocation.number_of_days - allocation.leaves_taken
                if allocation.date_from < cutoff_dates[0]:
                    leave_type["pre_1978"] += unused
                elif allocation.date_from < cutoff_dates[1]:
                    leave_type["pre_1993"] += unused
                else:
                    leave_type["post_1993"] += unused
        return leaves_by_date

    def _l10n_au_get_unused_leave_totals(self):
        leaves_by_date = self._l10n_au_get_unused_leave_by_type()
        if not leaves_by_date:
            return defaultdict(lambda: {"annual": 0.0, "long_service": 0.0})
        return {
            payslip: {
                'annual': sum(leaves_data['annual'].values()),
                'long_service': sum(leaves_data['long_service'].values()),
            } for payslip, leaves_data in leaves_by_date.items()
        }

    def _l10n_au_get_leaves_for_withhold(self):
        self.ensure_one()
        leaves_by_date = self._l10n_au_get_unused_leave_by_type()
        leave_totals = self._l10n_au_get_unused_leave_totals()
        # Precomputed values or user input
        gross_totals = {
            "annual": self.input_line_ids.filtered(lambda x: x.code == 'AL').amount,
            "long_service": self.input_line_ids.filtered(lambda x: x.code == 'LSL').amount
        }
        leave_amounts = defaultdict(lambda: {
            "pre_1978": 0.0,
            "pre_1993": 0.0,
            "post_1993": 0.0,
        })
        unused_leaves_total = sum(gross_totals.values())
        # Total gross amount is split evenly on the number of day of leaves unused
        for leave_type, periods in leaves_by_date[self.id].items():
            if not leave_totals[self.id][leave_type]:
                continue
            for period, amount in periods.items():
                amount *= gross_totals[leave_type] / leave_totals[self.id][leave_type]
                leave_amounts[leave_type][period] = amount
        return leave_amounts, unused_leaves_total

    def _add_unused_leaves_to_payslip(self):
        """ Add the unused leaves to the payslip as input lines """
        if not (self.env.is_superuser() or self.env.user.has_group('hr_payroll.group_hr_payroll_user')):
            raise AccessError(_(
                "You don't have the access rights to link an expense report to a payslip. You need to be a payroll officer to do that.")
            )
        termination_slips = self.filtered(
            lambda p: p.country_code == "AU"
                and p.state in ["draft", "verify"]
                and p.l10n_au_termination_type
        )
        termination_slips.input_line_ids.filtered(lambda x: x.code in ['AL', 'LSL']).unlink()

        input_vals = []
        leaves_totals = termination_slips._l10n_au_get_unused_leave_totals()
        for payslip in termination_slips:
            daily_wage = payslip._get_daily_wage()
            annual_gross = leaves_totals[payslip.id]['annual'] * daily_wage
            long_service_gross = leaves_totals[payslip.id]['long_service'] * daily_wage
            if payslip.contract_id.l10n_au_leave_loading == 'regular':
                annual_gross *= 1 + payslip.contract_id.l10n_au_leave_loading_rate / 100
            if annual_gross:
                input_vals.append({
                    'name': _('Gross Unused Annual Leaves'),
                    'amount': annual_gross,
                    'input_type_id': self.env.ref('l10n_au_hr_payroll.input_unused_leave_annual').id,
                    'payslip_id': payslip.id,
                })
            if long_service_gross:
                input_vals.append({
                    'name': _('Gross Unused Long Service Leaves'),
                    'amount': long_service_gross,
                    'input_type_id': self.env.ref('l10n_au_hr_payroll.input_unused_leave_long_service').id,
                    'payslip_id': payslip.id,
                })
        self.env['hr.payslip.input'].create(input_vals)

    def _l10n_au_get_unused_leave_hours(self):
        # Only annual and long service leaves are to be taken into account for termination payments
        leaves = self.env["hr.leave.allocation"].search([
            ("state", "=", "validate"),
            ("holiday_status_id.l10n_au_leave_type", "in", ['annual', 'long_service']),
            ("employee_id", "=", self.employee_id.id),
            ("date_from", "<=", self.contract_id.date_end or self.date_to),
        ])
        unused_days = sum([(leave.number_of_days - leave.leaves_taken) for leave in leaves])
        return unused_days * self.contract_id.resource_calendar_id.hours_per_day

    def _l10n_au_calculate_marginal_withhold(self, leave_amount, coefficients, basic_amount):
        self.ensure_one()

        # For scale 4 (no tfn provided), cents are ignored when applying the rate.
        if self.employee_id.l10n_au_tax_treatment_category == "N" or \
            self.employee_id.l10n_au_tfn_declaration == '000000000':
            withhold = leave_amount * (coefficients / 100)
            return withhold

        # TFN provided, we apply the normal table to the amount / period.
        period = self.contract_id.schedule_pay
        amount_per_period = leave_amount / PERIODS_PER_YEAR[period]

        normal_withhold = self._l10n_au_compute_withholding_amount(basic_amount, period, coefficients, unused_leaves=True)
        leave_withhold = self._l10n_au_compute_withholding_amount(basic_amount + amount_per_period, period, coefficients, unused_leaves=True)

        extra_withhold = (leave_withhold - normal_withhold) * PERIODS_PER_YEAR[period]
        # <300 apply min(tax_table or 32%)
        if leave_amount < self._rule_parameter('rule_parameter_leaves_low_threshold_schedule_7'):
            return min(extra_withhold, leave_amount * self._rule_parameter('rule_parameter_leaves_low_withhold_schedule_7'))
        return extra_withhold

    def _l10n_au_calculate_long_service_leave_withholding(self, leave_withholding_rate, long_service_leaves, basic_amount):
        self.ensure_one()
        coefficients = self._l10n_au_tax_schedule_parameters()
        pre_1978 = long_service_leaves["pre_1978"]
        pre_1993 = long_service_leaves["pre_1993"]
        post_1993 = long_service_leaves["post_1993"]

        flat_part = pre_1993
        marginal_part = pre_1978 * 0.05

        if self.l10n_au_termination_type == "normal":
            marginal_part += post_1993
        else:
            flat_part += post_1993

        marginal_withhold = round(self._l10n_au_calculate_marginal_withhold(marginal_part, coefficients, basic_amount))
        flat_withhold = round(flat_part * float(leave_withholding_rate) / 100)
        return flat_withhold + marginal_withhold

    def _l10n_au_calculate_annual_leave_withholding(self, leave_withholding_rate, annual_leaves, basic_amount):
        self.ensure_one()
        coefficients = self._l10n_au_tax_schedule_parameters()
        pre_1993 = annual_leaves["pre_1993"]
        post_1993 = annual_leaves["post_1993"]

        flat_part = pre_1993
        marginal_part = 0.0

        if self.l10n_au_termination_type == "normal":
            marginal_part += post_1993
        else:
            flat_part += post_1993

        marginal_withhold = round(self._l10n_au_calculate_marginal_withhold(marginal_part, coefficients, basic_amount))
        flat_withhold = round(flat_part * float(leave_withholding_rate) / 100)

        return flat_withhold + marginal_withhold

    def _l10n_au_compute_unused_leaves_withhold(self):
        self.ensure_one()
        basic_amount = self.contract_id.wage
        leaves, leaves_total = self._l10n_au_get_leaves_for_withhold()
        if self.employee_id.l10n_au_withholding_variation == 'leaves':
            l10n_au_leave_withholding = self.employee_id.l10n_au_withholding_variation_amount
            return leaves_total * l10n_au_leave_withholding / 100

        l10n_au_leave_withholding = self._rule_parameter("l10n_au_leave_withholding_schedule_7")
        withholding = 0.0
        # 2. Calculate long service leave withholding
        withholding = self._l10n_au_calculate_long_service_leave_withholding(l10n_au_leave_withholding, leaves["long_service"], basic_amount)
        # 3. Calculate annual leave withholding
        withholding += self._l10n_au_calculate_annual_leave_withholding(l10n_au_leave_withholding, leaves["annual"], basic_amount)
        return withholding

    def _get_pea_amount(self):
        # Computed differently than the salary amounts
        # https://www.servicesaustralia.gov.au/protected-earnings-amount-when-deducting-child-support?context=23156#a1
        self.ensure_one()
        pea = self._rule_parameter("l10n_au_pea")
        schedule_pay = self.l10n_au_schedule_pay
        if schedule_pay == "monthly":
            pea = pea / 7 * 30.4375
        if schedule_pay == "bi-weekly":
            pea = pea * 2
        if schedule_pay == "daily":
            pea = pea / 7
        return ceil(pea * 100) / 100  # Round up 2 decimal places

    def _l10n_au_compute_child_support(self, net_earnings):
        """
        net_earnings: Net salary after tax withhold and garnishee child support.
        Compute the child support amount deducted from the net salary after tax withhold.
        The child support has two components:
            - A garnishee child support:
                This can be a periodic % or fixed amount, or a one time lump sum. Deducted with
                CHILD.SUPPORT.GARNISHEE rule.
            - A child support deduction:
                Amount set by ATO, this can only be withheld, if the remaining
                net earnings are above the Protected Earnings Amount.
        """
        self.ensure_one()
        pea = self._get_pea_amount()
        employee_id = self.employee_id
        withhold = 0.0
        if net_earnings > pea:
            net_over_pea = net_earnings - pea
            withhold += min(net_over_pea, employee_id.l10n_au_child_support_deduction)
        return withhold

    def _l10n_au_has_extra_pay(self):
        self.ensure_one()
        return self.contract_id._l10n_au_get_weeks_amount(self.date_to) == 53

    def _l10n_au_compute_backpay_withhold(self, net_salary, backpay, salary_withhold):
        """Compute withhold for back payments
        Args:
            net_salary (float): Net salary including the backpayments
            backpay (float): Backpay amount
            salary_withhold (float): Withholding amount for the salary
        """
        if self.employee_id.l10n_au_tax_treatment_category == "H":
            return 0
        backpay_per_period = round(backpay / PERIODS_PER_YEAR[self.contract_id.schedule_pay])
        coefficients = self._l10n_au_tax_schedule_parameters()
        total_withhold = self._l10n_au_compute_withholding_amount(net_salary + backpay_per_period, self.contract_id.schedule_pay, coefficients)

        backpay_withhold = total_withhold - abs(salary_withhold)
        backpay_withhold *= PERIODS_PER_YEAR[self.contract_id.schedule_pay]
        backpay_withhold = -min(backpay_withhold, backpay * self._rule_parameter('l10n_au_withholding_backpay') / 100)

        # Backpay HELP Withholding
        coefficients = self._rule_parameter("l10n_au_stsl")[
            "tax-free"
            if self.employee_id.l10n_au_tax_free_threshold
            or self.employee_id.is_non_resident
            else "no-tax-free"
        ]
        backpay_stsl_per_period = -self._l10n_au_compute_loan_withhold(net_salary + backpay_per_period, self.contract_id.schedule_pay, coefficients)
        salary_stsl = -self._l10n_au_compute_loan_withhold(net_salary, self.contract_id.schedule_pay, coefficients)
        backpay_stsl = (backpay_stsl_per_period - salary_stsl) * PERIODS_PER_YEAR[self.contract_id.schedule_pay]

        return backpay_withhold, backpay_stsl

    def _l10n_au_tax_schedule_parameters(self) -> float | list[tuple[float]]:
        self.ensure_one()
        employee = self.employee_id
        match employee.l10n_au_tax_treatment_category:
            case "R":  # Regular
                rates = self._rule_parameter("l10n_au_withholding_schedule_1")
                # Foreign or no TFN
                if employee.l10n_au_tfn_declaration != "000000000" and employee.is_non_resident:
                    return rates["foreign"]
                if employee.l10n_au_tfn_declaration == "000000000":
                    residence = "foreign" if employee.is_non_resident else "resident"
                    return rates["no-tfn"][residence]
                # TFN provided
                if employee.l10n_au_medicare_exemption == "F":
                    return rates["full-exemption"]
                elif employee.l10n_au_medicare_exemption == "H":
                    return rates["half-exemption"]
                # No exemption
                elif employee.l10n_au_medicare_exemption == "X":
                    tax_threshold = "tax-free" if employee.l10n_au_tax_free_threshold else "no-tax-free"
                    return rates[tax_threshold]
            case "A":  # Actors
                rates = self._rule_parameter("l10n_au_withholding_schedule_3")
                if employee.l10n_au_tax_treatment_option_actor == "P":
                    if not employee.birthday:
                        raise ValidationError(_("In order to process this payslip, a birth date should be set on the private information tab of the employee's form view."))
                    # if age less than 18, use underage
                    if relativedelta(date.today(), employee.birthday).years < 18:
                        if self.contract_id.schedule_pay not in ["weekly", "fortnightly", "monthly"]:
                            raise ValidationError(_("The pay schedule for this employee is not supported for underage actors."))
                        return rates["promotional"]["underage"][self.contract_id.schedule_pay]
                    # if age greater than 18
                    tfn_status = 'tfn' if employee.l10n_au_tfn_declaration != "000000000" else 'no-tfn'
                    return rates["promotional"][tfn_status]
                elif employee.l10n_au_tax_treatment_option_actor == "D":
                    # Foreigner or no tfn
                    if employee.is_non_resident and employee.l10n_au_tfn_declaration != "000000000":
                        return rates["foreigner"]
                    elif employee.is_non_resident and employee.l10n_au_tfn_declaration == "000000000":
                        return rates["no-tfn"]["foreign"]
                    elif not employee.is_non_resident and employee.l10n_au_tfn_declaration == "000000000":
                        return rates["no-tfn"]["resident"]
                # Resident with tfn
                tax_threshold = "tax-free" if employee.l10n_au_tax_free_threshold else "no-tax-free"
                return rates[tax_threshold]
            case "C":  # Horticulture & Shearing
                rates = self._rule_parameter("l10n_au_withholding_schedule_2")
                tfn_status = 'tfn' if employee.l10n_au_tfn_declaration != "000000000" else 'no-tfn'
                if employee.is_non_resident:
                    return rates["foreign"][tfn_status]
                else:
                    return rates["resident"][tfn_status]
            case "S":  # Seniors & Pensioners
                rates = self._rule_parameter("l10n_au_withholding_schedule_9")
                # No TFN provided
                if employee.l10n_au_tfn_declaration == "000000000":
                    return rates["no-tfn"]["foreign"] if employee.is_non_resident else rates["no-tfn"]["resident"]
                # TFN provided
                if employee.l10n_au_tfn_declaration != "000000000":
                    if employee.l10n_au_tax_treatment_option_seniors == "S":
                        return rates["single"]
                    elif employee.l10n_au_tax_treatment_option_seniors == "M":
                        return rates["couple"]
                    elif employee.l10n_au_tax_treatment_option_seniors == "I":
                        return rates["illness-separated"]
            case "H":  # Working Holiday Makers
                rates = self._rule_parameter("l10n_au_withholding_schedule_15")
                # No TFN
                if employee.l10n_au_tfn_declaration == "000000000":
                    return rates["no-tfn"]
                # TFN Provided
                if self.company_id.l10n_au_registered_for_whm:
                    return rates["registered"]
                else:
                    return rates["unregistered"]
            case "W":  # Seasonal Worker Program
                rate = self._rule_parameter("l10n_au_withholding_schedule_palm")
                if self.company_id.l10n_au_registered_for_palm:
                    return rate['registered']
                return rate['unregistered']
            case "F":  # Foreign Resident
                return self._rule_parameter("l10n_au_withholding_foreign_resident")['foreign']
            case "N":
                rates = self._rule_parameter("l10n_au_withholding_no_tfn")
                return rates["foreign"] if employee.is_non_resident else rates["resident"]
            case "D":
                raise ValidationError(_("The tax treatment category 'D' is not yet supported."))
            case "V":
                rate = self._rule_parameter("l10n_au_withholding_schedule_10")
                if employee.l10n_au_tax_treatment_option_voluntary == "C":
                    return employee.l10n_au_comissioners_installment_rate or rate
                elif employee.l10n_au_tax_treatment_option_voluntary == "O":
                    return rate

        # In case no option satisfied. Config issue
        raise UserError(_(
            "The Employee '%(employee)s' with tax treatment category '%(category)s' has no valid tax schedule.",
            employee=employee.name, category=employee.l10n_au_tax_treatment_category
        ))

    def _get_regular_worked_hours(self):
        """
        Get the worked hours for the payslip except for the overtime hours.
        """
        self.ensure_one()
        overtime_days = self.worked_days_line_ids.filtered(lambda d: d.work_entry_type_id.l10n_au_work_stp_code == 'T')
        return self.sum_worked_hours - sum(overtime_days.mapped("number_of_hours"))
