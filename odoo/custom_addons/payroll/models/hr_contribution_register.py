# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrContributionRegister(models.Model):
    _name = "hr.contribution.register"
    _description = "Contribution Register"

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company,
    )
    partner_id = fields.Many2one("res.partner", string="Partner")
    name = fields.Char(required=True)
    register_line_ids = fields.One2many(
        "hr.payslip.line", "register_id", string="Register Line", readonly=True
    )
    note = fields.Text(string="Description")
