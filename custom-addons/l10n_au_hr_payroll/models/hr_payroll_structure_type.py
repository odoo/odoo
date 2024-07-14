# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrPayrollStructureType(models.Model):
    _inherit = "hr.payroll.structure.type"

    l10n_au_default_input_type_ids = fields.Many2many(
        "hr.payslip.input.type",
        string="Default Allowances",
        help="Default allowances for this structure type")
    l10n_au_tax_treatment_category = fields.Selection(
        selection=[
            ("R", "(R) Regular"),
            ("A", "(A) Actor"),
            ("C", "(C) Horticulture & Shearing"),
            ("S", "(S) Seniors & Pensioners"),
            ("H", "(H) Working Holiday Makers"),
            ("W", "(W) Seasonal Worker Program"),
            ("F", "(F) Foreign Resident"),
            ("N", "(N) No TFN"),
            ("D", "(D) ATO-defined"),
            ("V", "(V) Voluntary Agreement")],
        default="R",
        required=True,
        string="Tax Treatment Category")
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
        string="Income Stream Type",
        default="SAW",
        required=True)
