# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _


class HrTalentPool(models.Model):
    _name = "hr.talent.pool"
    _description = "Talent Pool"
    _inherit = ["mail.thread"]

    active = fields.Boolean(default=True)
    name = fields.Char(string="Title", required=True, translate=True)
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company,
        tracking=True,
    )
    pool_manager = fields.Many2one(
        "res.users",
        "Pool Manager",
        domain="[('share', '=', False), ('company_ids', 'in', company_id)]",
        tracking=True,
        store=True,
        readonly=False,
    )
    talent_ids = fields.Many2many(
        comodel_name="hr.applicant", string="Talent", groups="base.group_user"
    )
    no_of_talents = fields.Integer(
        compute="_compute_talent_count",
        string="Current Number of Employees",
        help="Number of employees currently occupying this job position.",
    )
    description = fields.Html(string="Job Description", sanitize_attributes=False)
    color = fields.Integer("Color")
    tags = fields.Integer("Tags")  # TODO fix

    def _compute_talent_count(self):
        for pool in self:
            pool.no_of_talents = 99
