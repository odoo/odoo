from typing import Self

from odoo import api, fields, models
from odoo.api import ValuesType

from ..tools import debug_log as dbg


class ProjectCollaborator(models.Model):
    _name = "project.collaborator"
    _description = "Collaborators in project shared"

    project_id = fields.Many2one(
        comodel_name="project.project",
        string="Project Shared",
        export_string_translation=False,
        readonly=True,
        required=True,
        domain=[
            ("privacy_visibility", "in", ["portal", "invited_users"]),
            ("is_template", "=", False),
        ],
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Collaborator",
        export_string_translation=False,
        readonly=True,
        required=True,
    )
    partner_email = fields.Char(
        related="partner_id.email",
        export_string_translation=False,
    )
    access_mode = fields.Selection(
        selection=[
            ("view", "View"),
            ("edit", "Edit"),
            ("advanced_edit", "Advanced Edit"),
        ],
        default="view",
        required=True,
        help="View: read the tasks and write in their chatter.\n"
        "Edit: also create and update tasks.\n"
        "Advanced Edit: also move tasks between steps and change their priority.",
    )

    _unique_collaborator = models.Constraint(
        "UNIQUE(project_id, partner_id)",
        "A collaborator cannot be selected more than once in the project sharing access. Please remove duplicate(s) and try again.",
    )

    @api.depends("project_id", "partner_id")
    def _compute_display_name(self) -> None:
        for collaborator in self:
            collaborator.display_name = f"{collaborator.project_id.display_name} - {collaborator.partner_id.display_name}"

    @dbg.timed
    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> Self:
        dbg.lifecycle.debug(
            "project.collaborator.create: %d vals, keys=%s",
            len(vals_list),
            dbg.vals_keys(vals_list),
        )
        collaborator = self.env["project.collaborator"].search([], limit=1)
        project_collaborators = super().create(vals_list)
        if not collaborator:
            dbg.pipeline.debug(
                "[collaborator:%s] first collaborator -> enable portal sharing rules",
                dbg.rec(project_collaborators),
            )
            self._update_project_sharing_portal_rules(True)
        return project_collaborators

    @dbg.timed
    def unlink(self) -> bool:
        dbg.lifecycle.debug("project.collaborator.unlink %s", dbg.rec(self))
        revoked = [
            (collaborator.project_id, collaborator.partner_id.id)
            for collaborator in self.sudo()
        ]
        res = super().unlink()
        for project, partner_id in revoked:
            project.message_unsubscribe(partner_ids=[partner_id])
        collaborator = self.env["project.collaborator"].search([], limit=1)
        if not collaborator:
            dbg.pipeline.debug(
                "[collaborator] last collaborator removed -> disable portal "
                "sharing rules"
            )
            self._update_project_sharing_portal_rules(False)
        return res

    @api.model
    def _update_project_sharing_portal_rules(self, active: bool) -> None:
        access_project_sharing_portal = self.env.ref(
            "project.access_project_sharing_task_portal"
        ).sudo()
        dbg.logic.debug(
            "_update_project_sharing_portal_rules(active=%s): access rule was %s",
            active,
            access_project_sharing_portal.active,
        )
        if access_project_sharing_portal.active != active:
            access_project_sharing_portal.write({"active": active})

        task_portal_ir_rule = self.env.ref(
            "project.project_task_rule_portal_project_sharing"
        ).sudo()
        if task_portal_ir_rule.active != active:
            task_portal_ir_rule.write({"active": active})
