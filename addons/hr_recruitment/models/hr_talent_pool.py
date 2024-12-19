# Part of Odoo. See LICENSE file for full copyright and licensing details.
from random import randint

from odoo import api, fields, models, SUPERUSER_ID, _


class HrTalentPool(models.Model):
    _name = "hr.talent.pool"
    _description = "Talent Pool"
    _inherit = ["mail.thread"]

    def _get_default_color(self):
        return randint(1, 11)

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
        default=lambda self: self.env.user if self.env.user.id != SUPERUSER_ID else False,
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
        string="# Talents",
        help="The number of talents in this talent pool.",
    )
    description = fields.Html(string="Job Description", sanitize_attributes=False)
    color = fields.Integer(string='Color', default=_get_default_color)
    categ_ids = fields.Many2many(
        comodel_name="hr.applicant.category",
        string="Tags",
        store=True,
        readonly=False,
    )

    def _compute_talent_count(self):
        for pool in self:
            pool.no_of_talents = len(pool.talent_ids)
