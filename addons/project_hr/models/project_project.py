from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.libs.debug_log import DebugLog
from odoo.tools import LazyTranslate

_lt = LazyTranslate(__name__)
_debug = DebugLog(__name__)


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
            _debug.logic(
                "project_manager_user_followed_employee",
                project=project,
                employee=project.employee_id,
                user=project.employee_id.user_id,
            )
            project.user_id = project.employee_id.user_id

    def _get_fields_assignment(self) -> set[str]:
        return super()._get_fields_assignment() | {"employee_id"}

    def _get_assigned_users(self, values):
        users = super()._get_assigned_users(values)
        if values.get("employee_id"):
            users |= (
                self.env["hr.employee"].browse(values["employee_id"]).sudo().user_id
            )
        return users

    @api.model
    def _prepare_assignment_vals(self, users):
        user = users[:1]
        if not user:
            return {"employee_id": False}
        employee = self._get_manager_employee(user)
        if not employee:
            _debug.logic("project_manager.refused", reason="no_employee", user=user)
            raise UserError(
                self.env._(
                    "%(user)s holds no employee record. A project manager is an "
                    "employee; create the employee first.",
                    user=user.display_name,
                )
            )
        return {"employee_id": employee.id}

    @api.model
    def _get_manager_employee(self, user):
        employees = self.env["hr.employee"].sudo()
        return employees.search(
            [("user_id", "=", user.id), ("company_id", "=", self.env.company.id)],
            limit=1,
        ) or employees.search([("user_id", "=", user.id)], limit=1)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if "user_id" not in vals or "employee_id" in vals:
                continue
            user = self.env["res.users"].browse(vals.pop("user_id"))
            vals.update(self._prepare_assignment_vals(user))
        return super().create(vals_list)

    def write(self, vals):
        if "user_id" in vals and "employee_id" not in vals:
            vals = dict(vals)
            user = self.env["res.users"].browse(vals.pop("user_id"))
            vals.update(self._prepare_assignment_vals(user))
        return super().write(vals)
