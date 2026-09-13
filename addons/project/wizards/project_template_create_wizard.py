from typing import Any, Self

from odoo import Command, api, fields, models

from ..tools import debug_log as dbg


class ProjectTemplateCreateWizard(models.TransientModel):
    _name = "project.template.create.wizard"
    _description = "Project Template create Wizard"

    def _default_role_to_users_ids(self) -> list[list]:
        res = []
        template = self.env["project.project"].browse(
            self.env.context.get("template_id")
        )
        if template:
            res = [
                Command.create({"role_id": role.id})
                for role in template.task_ids.role_ids
            ]
        return res

    name = fields.Char(required=True)
    date_start = fields.Date(string="Start Date")
    date = fields.Date(string="Expiration Date")
    alias_name = fields.Char()
    alias_domain_id = fields.Many2one(comodel_name="mail.alias.domain")
    template_id = fields.Many2one(
        comodel_name="project.project",
        default=lambda self: self.env.context.get("template_id"),
    )
    template_has_dates = fields.Boolean(compute="_compute_template_has_dates")
    role_to_users_ids = fields.One2many(
        comodel_name="project.template.role.to.users.map",
        inverse_name="wizard_id",
        default=_default_role_to_users_ids,
    )

    @api.depends("template_id")
    def _compute_template_has_dates(self) -> None:
        for wizard in self:
            wizard.template_has_dates = (
                wizard.template_id.date_start and wizard.template_id.date
            )

    def _get_fields_template_whitelist(self) -> list[str]:
        return ["name", "date_start", "date", "alias_name", "alias_domain_id"]

    @dbg.timed
    def _create_project_from_template(self) -> Self:
        field_values = self._convert_to_write(
            {
                fname: self[fname]
                for fname in self._fields.keys() & self._get_fields_template_whitelist()
            }
        )
        dbg.pipeline.debug(
            "[template:%s] create wizard -> action_create_from_template values=%s "
            "role mappings=%d",
            self.template_id.id,
            dbg.keys(field_values),
            len(self.role_to_users_ids),
        )
        return self.template_id.action_create_from_template(
            values=field_values, role_to_users_mapping=self.role_to_users_ids
        )

    def action_create_project_from_template(self) -> dict[str, Any]:
        return self._create_project_from_template().action_view_tasks()

    @api.model
    def action_view_template_view(self) -> dict[str, Any]:
        view = self.env.ref(
            "project.project_project_view_form_simplified_template",
            raise_if_not_found=False,
        )
        if not view:
            return {}
        return {
            "name": self.env._(
                "Create a Project from Template %s",
                self.env.context.get("template_name"),
            ),
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "views": [(view.id, "form")],
            "res_model": "project.template.create.wizard",
            "target": "new",
            "context": {
                key: value
                for key, value in self.env.context.items()
                if not key.startswith("default_")
            },
        }


class ProjectTemplateRoleToUsersMap(models.TransientModel):
    _name = "project.template.role.to.users.map"
    _description = "Project role to users mapping"

    wizard_id = fields.Many2one(
        comodel_name="project.template.create.wizard",
        export_string_translation=False,
    )
    role_id = fields.Many2one(
        comodel_name="resource.role",
        string="Project Role",
        required=True,
    )
    user_ids = fields.Many2many(
        comodel_name="res.users",
        string="Assignees",
        domain=[("share", "=", False), ("active", "=", True)],
    )
