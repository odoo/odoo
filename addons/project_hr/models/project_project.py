from odoo import api, fields, models
from odoo.tools import LazyTranslate

_lt = LazyTranslate(__name__)


class ProjectProject(models.Model):
    _name = "project.project"
    _inherit = ["mixin.hr", "project.project"]

    employee_id = fields.Many2one(
        comodel_name="hr.employee",
        string="Project Manager",
        default=lambda self: self.env["hr.employee"].search(
            [
                ("user_id", "=", self.env.uid),
                ("company_id", "=", self.env.company.id),
            ],
            limit=1,
        ),
        falsy_value_label=_lt("👤 No Manager"),
        tracking=True,
    )

    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Project Manager (User)",
        compute="_compute_user_id",
        default=None,
        store=True,
        readonly=True,
        tracking=False,
    )

    @api.depends("employee_id.user_id")
    def _compute_user_id(self):
        for project in self:
            project.user_id = project.employee_id.user_id
