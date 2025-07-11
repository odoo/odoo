# Part of Odoo. See LICENSE file for full copyright and licensing details.
from random import randint

from odoo import fields, models


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
        default=lambda self: self.env.user,
        domain="[('share', '=', False), ('company_ids', 'in', company_id)]",
        tracking=True,
        store=True,
        readonly=False,
    )
    talent_ids = fields.Many2many(comodel_name="hr.applicant", string="Talent", groups="base.group_user")
    no_of_talents = fields.Integer(
        compute="_compute_talent_count",
        string="# Talents",
        help="The number of talents in this talent pool.",
    )
    description = fields.Html(string="Talent Pool Description")
    color = fields.Integer(string="Color", default=_get_default_color)
    categ_ids = fields.Many2many(
        comodel_name="hr.applicant.category",
        string="Tags",
        store=True,
        readonly=False,
    )

    def _compute_talent_count(self):
        talents = self.env["hr.applicant"]._read_group(
            domain=[("talent_pool_ids", "in", self.ids)], groupby=["talent_pool_ids"], aggregates=["__count"]
        )
        talent_data = {talent_pool.id: count for talent_pool, count in talents}
        for pool in self:
            pool.no_of_talents = talent_data.get(pool.id, 0)

    def action_talent_pool_add_talents(self):
        self.ensure_one()
        return {
            "name": self.env._("Create Talent"),
            "type": "ir.actions.act_window",
            "res_model": "hr.applicant",
            "views": [[False, "form"]],
            "context": {
                "default_talent_pool_ids": [self.id],
            },
        }
