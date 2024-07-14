# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from datetime import datetime, date
from math import floor
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _

PERIODS_PER_YEAR = {
    "daily": 260,
    "weekly": 52,
    "bi-weekly": 26,
    "semi-monthly": 24,
    "monthly": 12,
    "bi-monthly": 6,
    "quarterly": 4,
    "semi-annually": 2,
    "yearly": 1,
}


class HrPayslip(models.Model):
    _inherit = "hr.payslip"

    l10n_au_income_stream_type = fields.Selection(
        related="contract_id.l10n_au_income_stream_type")
    l10n_au_foreign_tax_withheld = fields.Float(
        string="Foreign Tax Withheld",
        help="Foreign tax withheld for the current financial year")
    l10n_au_exempt_foreign_income = fields.Float(
        string="Exempt Foreign Income",
        help="Exempt foreign income for the current financial year")
    l10n_au_allowance_withholding = fields.Float(
        string="Withholding for Allowance",
        help="Amount to be withheld from allowances")
    l10n_au_schedule_pay = fields.Selection(related="contract_id.schedule_pay", store=True, index=True)
    l10n_au_termination_type = fields.Selection([
        ("normal", "Non-Genuine Redundancy"),
        ("genuine", "Genuine Redundancy"),
    ], required=True, default="normal", string="Termination Type")

    def _get_base_local_dict(self):
        res = super()._get_base_local_dict()
        res.update({
            "year_slips": self._l10n_au_get_year_to_date_slips(self.date_from),
            "ytd_total": self._l10n_au_get_year_to_date_totals(self.date_from),
        })
        return res

    def _get_daily_wage(self):
        period = self.struct_id.schedule_pay
        wage = self.contract_id.wage
        if period == "daily":
            return wage
        if period == "weekly":
            return wage / 5
        if period == "bi-weekly":
            return wage / 10
        if period == "monthly":
            return wage * 3 / 13 / 5
        if period == "quarterly":
            return wage / 13 / 5
        return wage

    def _compute_input_line_ids(self):
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
        return super()._compute_input_line_ids()

    def _l10n_au_get_financial_year_start(self, date):
        if date.month < 7:
            return date + relativedelta(years=-1, month=7, day=1)
        return date + relativedelta(month=7, day=1)

    def _l10n_au_get_financial_year_end(self, date):
        if date.month < 7:
            return date + relativedelta(month=6, day=30)
        return date + relativedelta(years=1, month=6, day=30)

    @api.model
    def _get_dashboard_warnings(self):
        res = super()._get_dashboard_warnings()

        employees_default_title = _('Employees')
        self.env.cr.execute("""
            SELECT DISTINCT e.id
            FROM hr_employee e
            WHERE (
                e.work_phone IS NULL
                OR e.private_street IS NULL
                OR e.private_city IS NULL
                OR e.birthday IS NULL
            )
            AND e.company_id = any(%s)
            AND e.active
        """, [self.env.companies.ids])
        if self.env.cr.rowcount:
            employees_missing_info = [e[0] for e in self.env.cr.fetchall()]
            res.append({
                'string': _('Employees with missing required information'),
                'count': len(employees_missing_info),
                'action': self._dashboard_default_action(employees_default_title, 'hr.employee', employees_missing_info),
            })

        self.env.cr.execute("""
            SELECT DISTINCT e.id
              FROM hr_employee e
             WHERE e.l10n_au_tfn_declaration = '111111111'
               AND e.create_date < NOW() - INTERVAL '28 days'
               AND e.company_id = any(%s)
               AND e.active
        """, [self.env.companies.ids])
        if self.env.cr.rowcount:
            employees_late_tfn = [e[0] for e in self.env.cr.fetchall()]
            res.append({
                'string': _('Employees who have not provided a TFN declaration after 28 days'),
                'count': len(employees_late_tfn),
                'action': self._dashboard_default_action(employees_default_title, 'hr.employee', employees_late_tfn),
            })

        return res

    def _l10n_au_get_year_to_date_slips(self, date_from):
        start_year = self._l10n_au_get_financial_year_start(date_from)
        year_slips = self.env["hr.payslip"].search([
            ("employee_id", "=", self.employee_id.id),
            ("company_id", "=", self.company_id.id),
            ("state", "in", ["paid", "done"]),
            ("date_from", ">=", start_year),
            ("date_from", "<=", date_from),
        ], order="date_from")
        if self.env.context.get('l10n_au_include_current_slip'):
            year_slips |= self
        return year_slips

    def _l10n_au_get_year_to_date_totals(self, date_from):
        year_slips = self._l10n_au_get_year_to_date_slips(date_from)
        totals = {
            "slip_lines": defaultdict(lambda: defaultdict(float)),
            "worked_days": defaultdict(lambda: defaultdict(float)),
            "periods": len(year_slips),
        }
        for line in year_slips.line_ids:
            totals["slip_lines"][line.category_id.name]["total"] += line.total
            totals["slip_lines"][line.category_id.name][line.code] += line.total
        for line in year_slips.worked_days_line_ids:
            totals["worked_days"][line.work_entry_type_id]["amount"] += line.amount
        return totals

    @api.model
    def _l10n_au_compute_weekly_earning(self, amount, period):
        if period == "monthly" and round(amount % 1, 2) == 0.33:
            amount += 0.01
        weekly_amount = self._l10n_au_convert_amount(amount, period, "weekly")
        return floor(weekly_amount) + 0.99

    @api.model
    def _l10n_au_convert_amount(self, amount, period_from, period_to):
        coefficient = PERIODS_PER_YEAR[period_from] / PERIODS_PER_YEAR[period_to]
        return amount * coefficient

    def _l10n_au_compute_withholding_amount(self, period_earning, period, coefficients):
        self.ensure_one()
        employee_id = self.employee_id
        contract = self.contract_id
        # if custom withholding rate
        if contract.l10n_au_withholding_variation:
            return period_earning * contract.l10n_au_withholding_variation_amount / 100

        weekly_earning = self._l10n_au_compute_weekly_earning(period_earning, period)
        weekly_withhold = 0.0

        if employee_id.l10n_au_scale == "4":
            coefficients = self._rule_parameter("l10n_au_withholding_no_tfn")
            weekly_withhold = floor(weekly_earning) * coefficients["foreign"] if employee_id.is_non_resident else coefficients["national"]
            return self._l10n_au_convert_amount(weekly_withhold, "weekly", period)
        coefficients = coefficients[employee_id.l10n_au_scale]
        for coef in coefficients:
            if coef[0] == "inf" or weekly_earning < coef[0]:
                weekly_withhold = coef[1] * weekly_earning - coef[2]
                break

        amount = round(weekly_withhold)
        period_amount = self._l10n_au_convert_amount(amount, "weekly", period)
        if period in ["daily", "monthly"]:
            period_amount = round(period_amount)
        return period_amount

    def _l10n_au_compute_medicare_adjustment(self, period_earning, period, params):
        self.ensure_one()
        params = params.copy()
        employee_id = self.employee_id
        if employee_id.children and employee_id.marital in ["cohabitant", "married"]:
            params["MLFT"] += employee_id.children * params["ADDC"]

        params["MLFT"] = round(params["MLFT"] / params["WFTD"], 2)
        params["SOP"] = round(params["MLFT"] * params["SOPM"] / params["SOPD"])
        weekly_earning = self._l10n_au_compute_weekly_earning(period_earning, period)

        adjustment = 0.0
        if weekly_earning < params["WEST"]:
            adjustment = (weekly_earning - params["WLA"]) * params["SOPM"]
        elif weekly_earning < params["MLFT"]:
            adjustment = weekly_earning * params["ML"]
        elif weekly_earning < params["SOP"]:
            adjustment = (params["MLFT"] * params["ML"]) - ((weekly_earning - params["MLFT"]) * params["SOPD"])

        amount = round(adjustment)
        period_amount = self._l10n_au_convert_amount(amount, "weekly", period)
        if period in ["daily", "monthly"]:
            period_amount = round(period_amount)
        return period_amount

    def _l10n_au_compute_lumpsum_withhold(self, lumpsum):
        '''
        Withholding for back payments is calculated by apportioning it over the number of periods it applies for and
        summing the difference in withholding over every period.
        '''
        self.ensure_one()
        return lumpsum * 0.47

    def _l10n_au_compute_loan_withhold(self, period_earning, period, coefficients):
        self.ensure_one()
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

    def _l10n_au_compute_termination_withhold(self, employee_id, ytd_total):
        self.ensure_one()
        etp_withholding = self._rule_parameter("l10n_au_etp_withholding")
        etp_cap = self._rule_parameter("l10n_au_etp_cap")
        etp_whoic_cap = self._rule_parameter("l10n_au_whoic_cap") - ytd_total["slip_lines"]["Gross"]["total"]
        genuine_redundancy = self.env.ref("l10n_au_hr_payroll.input_genuine_redundancy")
        early_retirement = self.env.ref("l10n_au_hr_payroll.input_early_retirement_scheme")

        preservation_age = datetime.strptime(self._rule_parameter("l10n_au_preservation_age"), "%Y-%m-%d").date()
        under_over = (employee_id.birthday or date.today()) > preservation_age

        base = self._rule_parameter("l10n_au_tax_free_base")
        yearly = self._rule_parameter("l10n_au_tax_free_year")
        complete_years_of_service = relativedelta(self.date_to, employee_id.first_contract_date).years
        tax_free_base_limit = base + yearly * complete_years_of_service

        rate_over_cap = etp_withholding["over_cap"]

        withholding = 0.0
        non_taxable_amount = 0.0
        for inpt in self.input_line_ids.sorted(key=lambda i: i.input_type_id.l10n_au_etp_cap, reverse=True):
            if not inpt.input_type_id.l10n_au_is_etp:
                continue
            taxable_amount = inpt.amount
            # 1. if the input is a genuine_redundancy or early retirement, calculate the taxable amount
            if inpt.input_type_id in [genuine_redundancy, early_retirement]:
                non_taxable_amount = min(tax_free_base_limit, inpt.amount)
                taxable_amount = max(0, inpt.amount - tax_free_base_limit)
            # 2. get the correct cap and calculate taxable amount under and over cap
            rate_up_to_cap = etp_withholding[inpt.input_type_id.l10n_au_etp_type]["over" if under_over else "under"]
            cap_to_use = min(etp_cap, etp_whoic_cap)
            amount_under_cap = min(cap_to_use, taxable_amount)
            amount_over_cap = max(0, taxable_amount - cap_to_use)
            # 3. calculate withholding
            withholding += amount_under_cap * rate_up_to_cap / 100
            withholding += amount_over_cap * rate_over_cap / 100
            etp_cap -= taxable_amount
        return round(withholding), non_taxable_amount

    def _l10n_au_get_leaves_for_withhold(self):
        self.ensure_one()
        cutoff_dates = [datetime(1978, 8, 16).date(), datetime(1993, 8, 17).date()]
        leaves_by_date = {
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
            "leaves_amount": 0.0,
        }
        leaves = self.env["hr.leave.allocation"].search([
            ("employee_id", "=", self.employee_id.id),
            ("state", "=", "validate"),
        ])
        daily_wage = self._get_daily_wage()
        for leave in leaves:
            if leave.leaves_taken == leave.number_of_days:
                continue
            leave_type = leaves_by_date[leave.holiday_status_id.l10n_au_leave_type]
            amount = (leave.number_of_days - leave.leaves_taken) * daily_wage
            if leave.date_from < cutoff_dates[0]:
                leave_type["pre_1978"] += amount
            elif leave.date_from < cutoff_dates[1]:
                leave_type["pre_1993"] += amount
            else:
                leave_type["post_1993"] += amount
            leaves_by_date["leaves_amount"] += amount
        return leaves_by_date

    def _l10n_au_calculate_marginal_withhold(self, year_slips, leave_amount, coefficients):
        self.ensure_one()
        period = self.contract_id.schedule_pay
        amount_per_period = leave_amount / PERIODS_PER_YEAR[period]

        last_payslip = year_slips[-2] if len(year_slips) > 1 else False
        if not last_payslip:
            last_payslip = self

        normal_withhold = self._l10n_au_compute_withholding_amount(self.basic_wage, period, coefficients)
        leave_withhold = self._l10n_au_compute_withholding_amount(self.basic_wage + amount_per_period, period, coefficients)

        extra_withhold = leave_withhold - normal_withhold
        return extra_withhold * PERIODS_PER_YEAR[period]

    def _l10n_au_calculate_long_service_leave_withholding(self, year_slips, leave_withholding_rate, long_service_leaves):
        self.ensure_one()
        coefficients = self._rule_parameter("l10n_au_withholding_coefficients")["regular"]
        pre_1978 = long_service_leaves["pre_1978"]
        pre_1993 = long_service_leaves["pre_1993"]
        post_1993 = long_service_leaves["post_1993"]

        flat_part = pre_1993
        marginal_part = pre_1978 * 0.05

        if self.l10n_au_termination_type == "normal":
            marginal_part += post_1993
        else:
            flat_part += post_1993

        marginal_withhold = round(self._l10n_au_calculate_marginal_withhold(year_slips, marginal_part, coefficients))
        flat_withhold = round(flat_part * float(leave_withholding_rate) / 100)
        return flat_withhold + marginal_withhold

    def _l10n_au_calculate_annual_leave_withholding(self, year_slips, leave_withholding_rate, annual_leaves):
        self.ensure_one()
        coefficients = self._rule_parameter("l10n_au_withholding_coefficients")["regular"]
        pre_1993 = annual_leaves["pre_1993"]
        post_1993 = annual_leaves["post_1993"]

        flat_part = pre_1993
        marginal_part = 0.0

        if self.l10n_au_termination_type == "normal":
            marginal_part += post_1993
        else:
            flat_part += post_1993

        marginal_withhold = round(self._l10n_au_calculate_marginal_withhold(year_slips, marginal_part, coefficients))
        flat_withhold = round(flat_part * float(leave_withholding_rate) / 100)

        return flat_withhold + marginal_withhold

    def _l10n_au_compute_unused_leaves_withhold(self, year_slips):
        self.ensure_one()
        leaves = self._l10n_au_get_leaves_for_withhold()
        l10n_au_leave_withholding = self._rule_parameter("l10n_au_leave_withholding")
        withholding = 0.0
        # 2. Calculate long service leave withholding
        long_service_leaves = leaves["long_service"]
        withholding += self._l10n_au_calculate_long_service_leave_withholding(year_slips, l10n_au_leave_withholding, long_service_leaves)
        # 3. Calculate annual leave withholding
        annual_leaves = leaves["annual"]
        withholding += self._l10n_au_calculate_annual_leave_withholding(year_slips, l10n_au_leave_withholding, annual_leaves)
        return leaves["leaves_amount"], withholding, 0.0

    def _l10n_au_compute_child_support(self, net_earnings):
        self.ensure_one()
        pea = self._rule_parameter("l10n_au_pea")
        employee_id = self.employee_id
        withhold = 0.0

        # garnishee child support does not apply the pea, first apply the lumpsum deductions
        # then the regular deductions
        lumpsum_child_support = sum(self.input_line_ids.sudo().filtered(lambda inpt: inpt.input_type_id.code == 'CHILD_SUPPORT').mapped('amount'))
        lumpsum_child_support = min(net_earnings, lumpsum_child_support)
        withhold = lumpsum_child_support
        net_earnings -= withhold

        if net_earnings:
            if employee_id.l10n_au_child_support_garnishee == "fixed":
                withhold += min(net_earnings, employee_id.l10n_au_child_support_garnishee_amount)
            elif employee_id.l10n_au_child_support_garnishee == "percentage":
                withhold += net_earnings * employee_id.l10n_au_child_support_garnishee_amount
            net_earnings -= withhold

        if net_earnings > pea:
            net_over_pea = net_earnings - pea
            withhold += min(net_over_pea, employee_id.l10n_au_child_support_deduction)
        return withhold

    def _l10n_au_has_extra_pay(self):
        self.ensure_one()
        pay_day = int(self.contract_id.l10n_au_pay_day)
        today = fields.Date.today().replace(month=1, day=1)
        return today.weekday() == pay_day
