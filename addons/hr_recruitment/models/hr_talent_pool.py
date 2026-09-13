from odoo import fields, models


class HrTalentPool(models.Model):
    _name = "hr.talent.pool"
    _description = "Talent Pool"
    _inherit = ["mixin.mail.thread", "mixin.color"]

    active = fields.Boolean(default=True)
    name = fields.Char(
        string="Title",
        translate=True,
        required=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
        tracking=True,
    )
    pool_manager = fields.Many2one(
        comodel_name="res.users",
        default=lambda self: self.env.user,
        domain="[('share', '=', False), ('company_ids', 'in', company_id)]",
        tracking=True,
    )
    talent_ids = fields.Many2many(
        comodel_name="hr.applicant",
        groups="base.group_user",
    )
    no_of_talents = fields.Integer(
        string="# Talents",
        compute="_compute_no_of_talents",
        help="The number of talents in this talent pool.",
    )
    description = fields.Html(string="Talent Pool Description")
    color = fields.Integer(default=lambda self: self._default_color())
    categ_ids = fields.Many2many(
        comodel_name="hr.applicant.category",
        string="Tags",
    )

    def _compute_no_of_talents(self):
        talents = self.env["hr.applicant"]._read_group(
            domain=[("talent_pool_ids", "in", self.ids)],
            groupby=["talent_pool_ids"],
            aggregates=["__count"],
        )
        talent_data = {talent_pool.id: count for talent_pool, count in talents}
        for pool in self:
            pool.no_of_talents = talent_data.get(pool.id, 0)

    def action_talent_pool_add_talents(self):
        self.check_singleton()
        return {
            "name": self.env._("Create Talent"),
            "type": "ir.actions.act_window",
            "res_model": "hr.applicant",
            "views": [[False, "form"]],
            "context": {
                "default_talent_pool_ids": [self.id],
            },
        }
