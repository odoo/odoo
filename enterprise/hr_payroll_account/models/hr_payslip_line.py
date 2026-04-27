# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class HrPayslip(models.Model):
    _inherit = "hr.payslip.line"

    debit_tag_ids = fields.Many2many(
        string="Debit Tax Grids",
        comodel_name='account.account.tag',
        help="Tags assigned to this line will impact financial reports when translated into an accounting journal entry."
            "They will be applied on the debit account line in the journal entry.",
        compute="_compute_debit_tags",
    )
    credit_tag_ids = fields.Many2many(
        string="Credit Tax Grids",
        comodel_name='account.account.tag',
        help="Tags assigned to this line will impact financial reports when translated into an accounting journal entry."
            "They will be applied on the credit account line in the journal entry.",
        compute="_compute_credit_tags",
    )

    @api.depends('salary_rule_id')
    def _compute_debit_tags(self):
        # To be overridden for specific localisation cases
        for record in self:
            record.debit_tag_ids = record.salary_rule_id.debit_tag_ids.ids

    @api.depends('salary_rule_id')
    def _compute_credit_tags(self):
        # To be overridden for specific localisation cases
        for record in self:
            record.credit_tag_ids = record.salary_rule_id.credit_tag_ids.ids
