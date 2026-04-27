# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrPayrollStructureType(models.Model):
    _inherit = "hr.payroll.structure.type"

    l10n_au_default_input_type_ids = fields.Many2many(
        "hr.payslip.input.type",
        string="Default Allowances",
        help="Default allowances for this structure type")
