# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HRContract(models.Model):
    _inherit = "hr.contract"

    l10n_ae_housing_allowance = fields.Monetary(string="Housing Allowance")
    l10n_ae_transportation_allowance = fields.Monetary(string="Transportation Allowance")
    l10n_ae_other_allowances = fields.Monetary(string="Other Allowances")
    l10n_ae_is_dews_applied = fields.Boolean(string="Is DEWS Applied",
                                             help="Daman Investments End of Service Programme")
    l10n_ae_number_of_leave_days = fields.Integer(string="Number of Leave Days", default=30,
                                                  help="Number of leave days of gross salary to be added to the annual leave provision per month")
    l10n_ae_is_computed_based_on_daily_salary = fields.Boolean(string="Computed Based On Daily Salary",
                                                               help="If True, The EOS will be computed based on the daily salary provided rather than the basic salary")
    l10n_ae_eos_daily_salary = fields.Float(string="Daily Salary")

    _sql_constraints = [
        ('l10n_ae_hr_payroll_number_of_leave_days_constraint', 'CHECK(l10n_ae_number_of_leave_days >= 0)',
         'Number of Leave Days must be equal to or greater than 0')
    ]
