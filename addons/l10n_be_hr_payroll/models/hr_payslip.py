#-*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.tools import float_round


class Payslip(models.Model):
    _inherit = 'hr.payslip'

    def _get_base_local_dict(self):
        res = super()._get_base_local_dict()
        res.update({
            'compute_ip_deduction': compute_ip_deduction,
            'compute_withholding_taxes': compute_withholding_taxes,
            'compute_employment_bonus_employees': compute_employment_bonus_employees,
            'compute_special_social_cotisations': compute_special_social_cotisations,
            'compute_double_holiday_withholding_taxes': compute_double_holiday_withholding_taxes,
            'compute_thirteen_month_withholding_taxes': compute_thirteen_month_withholding_taxes,
        })
        return res


def compute_withholding_taxes(payslip, categories, worked_days, inputs):

    def compute_basic_bareme(value):
        if value <= 12860.0:
            basic_bareme = value * 0.2675
        elif value <= 19630.0:
            basic_bareme = 3440.05 + 0.428 * (value - 12860.00)
        elif value <= 40470.00:
            basic_bareme = 6337.61 + 0.4815 * (value - 19630.00)
        else:
            basic_bareme = 16372.07 + 0.535 * (value - 40470.0)
        return float_round(basic_bareme, precision_rounding=0.01)

    def convert_to_month(value):
        return float_round(value / 12.0, precision_rounding=0.01, rounding_method='DOWN')

    employee = payslip.contract_id.employee_id
    # PART 1: Withholding tax amount computation
    withholding_tax_amount = 0.0
    lower_bound = categories.GROSS - categories.GROSS % 15

    # yearly_gross_revenue = Revenu Annuel Brut
    yearly_gross_revenue = lower_bound * 12.0

    # yearly_net_taxable_amount = Revenu Annuel Net Imposable
    if yearly_gross_revenue <= 16033.33:
        yearly_net_taxable_revenue = yearly_gross_revenue * (1.0 - 0.3)
    else:
        yearly_net_taxable_revenue = yearly_gross_revenue - 4810.0

    # BAREME III: Non resident
    if employee.resident_bool:
        basic_bareme = compute_basic_bareme(yearly_net_taxable_revenue)
        withholding_tax_amount = convert_to_month(basic_bareme)
    else:
        # BAREME I: Isolated or spouse with income
        if employee.marital in ['divorced', 'single', 'widower'] or (employee.marital in ['married', 'cohabitant'] and employee.spouse_fiscal_status=='with income'):
            basic_bareme = max(compute_basic_bareme(yearly_net_taxable_revenue) - 2065.1, 0.0)
            withholding_tax_amount = convert_to_month(basic_bareme)

        # BAREME II: spouse without income
        if employee.marital in ['married', 'cohabitant'] and employee.spouse_fiscal_status=='without income':
            yearly_net_taxable_revenue_for_spouse = min(yearly_net_taxable_revenue * 0.3, 10930.0)
            basic_bareme_1 = compute_basic_bareme(yearly_net_taxable_revenue_for_spouse)
            basic_bareme_2 = compute_basic_bareme(yearly_net_taxable_revenue - yearly_net_taxable_revenue_for_spouse)
            withholding_tax_amount = convert_to_month(max(basic_bareme_1 + basic_bareme_2 - 4130.20, 0))

    # Reduction for isolated people and for other family charges
    if employee.marital in ['divorced', 'single', 'widower'] or (employee.spouse_net_revenue > 0.0 or employee.spouse_other_net_revenue > 0.0):
        if employee.marital in ['divorced', 'single', 'widower']:
            withholding_tax_amount -= 26.0
        if employee.marital == 'widower' or (employee.marital in ['divorced', 'single', 'widower'] and employee.dependent_children):
            withholding_tax_amount -= 36.0
        if employee.disabled:
            withholding_tax_amount -= 36.0
        if employee.other_dependent_people and employee.dependent_seniors:
            withholding_tax_amount -= 80 * employee.dependent_seniors
        if employee.other_dependent_people and employee.dependent_juniors:
            withholding_tax_amount -= 36.0 * employee.dependent_juniors
        if employee.marital in ['married', 'cohabitant'] and employee.spouse_fiscal_status=='with income' and employee.spouse_net_revenue <= 230.0:
            withholding_tax_amount -= 115.0
        if employee.marital in ['married', 'cohabitant'] and employee.spouse_fiscal_status=='with income' and not employee.spouse_net_revenue and employee.spouse_other_net_revenue <= 459.0:
            withholding_tax_amount -= 229.5
    if employee.marital in ['married', 'cohabitant'] and employee.spouse_net_revenue == 0.0 and employee.spouse_other_net_revenue == 0.0:
        if employee.disabled:
            withholding_tax_amount -= 36.0
        if employee.disabled_spouse_bool:
            withholding_tax_amount -= 36.0
        if employee.other_dependent_people and employee.dependent_seniors:
            withholding_tax_amount -= 80.0 * employee.dependent_seniors
        if employee.other_dependent_people and employee.dependent_juniors:
            withholding_tax_amount -= 36.0 * employee.dependent_juniors

    # Child Allowances
    if employee.dependent_children:
        if employee.dependent_children == 1:
            withholding_tax_amount -= 36.0
        if employee.dependent_children == 2:
            withholding_tax_amount -= 104.0
        if employee.dependent_children == 3:
            withholding_tax_amount -= 275.0
        if employee.dependent_children == 4:
            withholding_tax_amount -= 483.0
        if employee.dependent_children == 5:
            withholding_tax_amount -= 713.0
        if employee.dependent_children == 6:
            withholding_tax_amount -= 944.0
        if employee.dependent_children == 7:
            withholding_tax_amount -= 1174.0
        if employee.dependent_children >= 8:
            withholding_tax_amount -= 1428.0 + (employee.dependent_children - 8) * 256.0

    return - max(withholding_tax_amount, 0.0)

def compute_special_social_cotisations(payslip, categories, worked_days, inputs):
    employee = payslip.contract_id.employee_id
    wage = categories.BASIC
    if employee.resident_bool:
        result = 0.0
    elif employee.marital in ['divorced', 'single', 'widower'] or (employee.marital in ['married', 'cohabitant'] and employee.spouse_fiscal_status=='without income'):
        if 0.01 <= wage <= 1095.09:
            result = 0.0
        elif 1095.10 <= wage <= 1945.38:
            result = 0.0
        elif 1945.39 <= wage <= 2190.18:
            result = -min((wage - 1945.38) * 0.076, 18.60)
        elif 2190.19 <= wage <= 6038.82:
            result = -min(18.60 + (wage - 2190.18) * 0.011, 60.94)
        else:
            result = -60.94
    elif employee.marital in ['married', 'cohabitant'] and employee.spouse_fiscal_status=='with income':
        if 0.01 <= wage <= 1095.09:
            result = 0.0
        elif 1095.10 <= wage <= 1945.38:
            result = -9.30
        elif 1945.39 <= wage <= 2190.18:
            result = -min(max((wage - 1945.38) * 0.076, 9.30), 18.60)
        elif 2190.19 <= wage <= 6038.82:
            result = -min(18.60 + (wage - 2190.18) * 0.011, 51.64)
        else:
            result = -51.64
    return result

def compute_ip_deduction(payslip, categories, worked_days, inputs):
    tax_rate = 0.15
    ip_amount = categories.GROSSIP * payslip.contract_id.ip_wage_rate / 100.0
    if 0.0 <= ip_amount <= 15660:
        tax_rate = tax_rate / 2.0
    elif 15660.0 < ip_amount <= 31320:
        tax_rate = tax_rate * 3.0 / 4.0
    return - min(ip_amount * tax_rate, 11745)

def compute_employment_bonus_employees(payslip, categories, worked_days, inputs):
    salary = categories.BRUT
    if salary <= 1641.62:
        result = 201.62
    elif salary <= 2560.57:
        result = 201.62 - (0.2194 * (salary - 1641.62))
    return result

def compute_double_holiday_withholding_taxes(payslip, categories, worked_days, inputs):
    rates = [
        (8460.0, 0), (10830.0, 0.1917),
        (13775.0, 0.2120), (16520.0, 0.2625),
        (18690.0, 0.3130), (20870.0, 0.3433),
        (25230.0, 0.3634), (27450.0, 0.3937),
        (36360.0, 0.4239), (47480.0, 0.4744)]

    employee = payslip.contract_id.employee_id
    def find_rates(x):
        for a, b in rates:
            if x <= a:
                return b
        return 0.535

    # Up to 12 children
    children_exoneration = [0.0, 13329.0, 16680.0, 21820.0, 27560.0, 33300.0, 39040.0, 44780.0, 50520.0, 56260.0, 62000.0, 67740.0, 73480.0]
    # Only if no more than 5 children
    children_reduction = [(0, 0), (22940.0, 0.075), (22940.0, 0.2), (25235.0, 0.35), (29825.0, 0.55), (32120.0, 0.75)]

    n = employee.dependent_children
    yearly_revenue = categories.GROSS * 12.0

    if 0 < n < 13 and yearly_revenue <= children_exoneration[n]:
        yearly_revenue = yearly_revenue - (children_exoneration[n] - yearly_revenue)

    if n <= 5 and yearly_revenue <= children_reduction[n][0]:
        withholding_tax_amount = yearly_revenue * find_rates(yearly_revenue) * (1 - children_reduction[n][1])
    else:
        withholding_tax_amount = yearly_revenue * find_rates(yearly_revenue)
    return -withholding_tax_amount / 12.0

def compute_thirteen_month_withholding_taxes(payslip, categories, worked_days, inputs):
    employee = payslip.contract_id.employee_id
    rates = [
        (8460.0, 0), (10830.0, 0.2322),
        (13775.0, 0.2523), (16520.0, 0.3028),
        (18690.0, 0.2533), (20870.0, 0.3836),
        (25230.0, 0.4038), (27450.0, 0.4341),
        (36360.0, 0.4644), (47480.0, 0.5148)]

    def find_rates(x):
        for a, b in rates:
            if x <= a:
                return b
        return 0.535

    # Up to 12 children
    children_exoneration = [0.0, 13329.0, 16680.0, 21820.0, 27560.0, 33300.0, 39040.0, 44780.0, 50520.0, 56260.0, 62000.0, 67740.0, 73480.0]
    # Only if no more than 5 children
    children_reduction = [(0, 0), (22940.0, 0.075), (22940.0, 0.2), (25235.0, 0.35), (29825.0, 0.55), (32120.0, 0.75)]

    n = employee.dependent_children
    yearly_revenue = categories.GROSS * 12.0

    if 0 < n < 13 and yearly_revenue <= children_exoneration[n]:
        yearly_revenue = yearly_revenue - (children_exoneration[n] - yearly_revenue)

    if n <= 5 and yearly_revenue <= children_reduction[n][0]:
        withholding_tax_amount = yearly_revenue * find_rates(yearly_revenue) * (1 - children_reduction[n][1])
    else:
        withholding_tax_amount = yearly_revenue * find_rates(yearly_revenue)
    return -withholding_tax_amount / 12.0
