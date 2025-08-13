# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    module_payroll_account = fields.Boolean(string="Payroll Accounting")
    leaves_positive = fields.Boolean(
        config_parameter="payroll.leaves_positive",
        string="Leaves with positive values",
        help="In payslip worked days, leave days/hours have positive values",
    )
    allow_cancel_payslips = fields.Boolean(
        config_parameter="payroll.allow_cancel_payslips",
        string="Allow canceling confirmed payslips",
        help="Allow users to cancel confirmed payslips.",
    )
    prevent_compute_on_confirm = fields.Boolean(
        config_parameter="payroll.prevent_compute_on_confirm",
        string="Confirm payslips without recomputing",
        help="Prevent payslips from being recomputed when confirming them",
        default=True,
    )
    allow_edit_payslip_lines = fields.Boolean(
        config_parameter="payroll.allow_edit_payslip_lines",
        string="Allow editing payslip lines",
        help="Allow users to edit some payslip line fields manually",
        default=False,
    )
    require_code_and_category = fields.Boolean(
        config_parameter="payroll.require_code_and_category",
        string="Require code/category on rules, categories and structures",
        help="Require rule.code, rule.category, category.code, structure.code",
        default=False,
    )
