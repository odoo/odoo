# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrApplicant(models.Model):
    _name = "hr.applicant"
    _inherit = ["hr.applicant"]

    department_id = fields.Many2one(
        "hr.department",
        "Department",
        compute="_compute_department",
        store=True,
        readonly=True,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        tracking=True,
    )
    company_id = fields.Many2one(
        "res.company",
        "Company",
        compute="_compute_company",
        store=True,
        readonly=True,
        tracking=True,
    )
