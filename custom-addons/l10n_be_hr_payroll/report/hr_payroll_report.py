# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrPayrollReport(models.Model):
    _inherit = "hr.payroll.report"

    struct_id = fields.Many2one('hr.payroll.structure', 'Structure', readonly=True)
    l10n_be_atn_deduction = fields.Float('Benefit in Kind Deductions (All)', readonly=True)
    l10n_be_meal_voucher_count = fields.Float('Meal Voucher Count', readonly=True)
    l10n_be_meal_voucher_employer = fields.Float('Meal Voucher (Employer)', readonly=True)
    l10n_be_withholding_taxes_exemption = fields.Float('Withholding Taxes Exemption', readonly=True)

    def _select(self, additional_rules):
        return super()._select(additional_rules) + """,
                p.struct_id as struct_id,
                CASE WHEN wd.id = min_id.min_line THEN l10n_be_meal_voucher_count.quantity ELSE 0 END as l10n_be_meal_voucher_count,
                CASE WHEN wd.id = min_id.min_line THEN (c.meal_voucher_amount - 1.09) * l10n_be_meal_voucher_count.quantity ELSE 0 END as l10n_be_meal_voucher_employer,
                CASE WHEN wd.id = min_id.min_line THEN -SUM(COALESCE(l10n_be_deduction_atn.total, 0)) ELSE 0 END as l10n_be_atn_deduction,
                l10n_be_274_xx_line.amount as l10n_be_withholding_taxes_exemption
                """

    def _from(self, additional_rules):
        return super()._from(additional_rules) + """
                left join l10n_be_274_xx l10n_be_274_xx on (l10n_be_274_xx.date_start BETWEEN p.date_from AND p.date_to AND l10n_be_274_xx.date_end BETWEEN p.date_from AND p.date_to)
                left join l10n_be_274_xx_line l10n_be_274_xx_line on (l10n_be_274_xx_line.sheet_id = l10n_be_274_xx.id AND p.employee_id = l10n_be_274_xx_line.employee_id)
                left join hr_payslip_line l10n_be_meal_voucher_count on (l10n_be_meal_voucher_count.slip_id = p.id and l10n_be_meal_voucher_count.code = 'MEAL_V_EMP')
                left join hr_payslip_line l10n_be_deduction_atn on (l10n_be_deduction_atn.slip_id = p.id and l10n_be_deduction_atn.code in ('ATN.LAP', 'ATN.INT', 'ATN.MOB', 'ATN.CAR'))"""

    def _group_by(self, additional_rules):
        return super()._group_by(additional_rules) + """,
                p.struct_id,
                l10n_be_meal_voucher_count.quantity,
                l10n_be_274_xx_line.amount"""
