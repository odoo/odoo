from odoo import api, fields, models
from odoo.tools import LazyTranslate

_lt = LazyTranslate(__name__)


class ProjectProject(models.Model):
    """Extend project.project to use hr.employee as project manager identity.

    employee_id replaces user_id as the field users interact with.
    user_id is demoted to a computed stored field derived from
    employee_id.user_id so filters and downstream modules keep working.
    """

    _inherit = ["hr.mixin", "project.project"]

    employee_id = fields.Many2one(
        "hr.employee",
        string="Project Manager",
        tracking=True,
        default=lambda self: self.env["hr.employee"].search(
            [
                ("user_id", "=", self.env.uid),
                ("company_id", "=", self.env.company.id),
            ],
            limit=1,
        ),
        falsy_value_label=_lt("👤 No Manager"),
    )

    # Derived from employee_id; stored so "My Projects" domain filter
    # and any other user_id reference keeps working without changes.
    user_id = fields.Many2one(
        "res.users",
        compute="_compute_user_id",
        store=True,
        readonly=True,
        # Override parent's tracking=True and default=lambda self: self.env.user.
        tracking=False,
        default=None,
    )

    @api.depends("employee_id")
    def _compute_user_id(self):
        """Derive user_id from the assigned project manager employee."""
        for project in self:
            project.user_id = project.employee_id.user_id
