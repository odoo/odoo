import operator
from typing import Any

from odoo import Command, _, api, fields, models

from ..tools import debug_log as dbg


class ProjectShareWizard(models.TransientModel):
    _name = "project.share.wizard"
    _inherit = ["portal.share"]
    _description = "Project Sharing"

    @api.model
    def default_get(self, fields_list: list[str]) -> dict[str, Any]:
        active_model = self.env.context.get("active_model", "")
        active_id = self.env.context.get("active_id", False)
        if active_model == "project.collaborator":
            active_model = "project.project"
            active_id = self.env.context.get("default_project_id", False)
        default_fields = fields_list
        if "collaborator_ids" in fields_list:
            default_fields = list(dict.fromkeys([*fields_list, "res_model", "res_id"]))
        result = super(
            ProjectShareWizard,
            self.with_context(active_model=active_model, active_id=active_id),
        ).default_get(default_fields)
        if (
            "collaborator_ids" in fields_list
            and "collaborator_ids" not in result
            and result.get("res_model") == "project.project"
            and result.get("res_id")
        ):
            project = self.env["project.project"].browse(result["res_id"]).exists()
            collaborator_vals_list = [
                {
                    "partner_id": collaborator.partner_id.id,
                    "partner_name": collaborator.partner_id.display_name,
                    "access_mode": collaborator.access_mode,
                }
                for collaborator in project.collaborator_ids
            ]
            dbg.logic.debug(
                "project.share.wizard.default_get [project:%s]: %d prefilled rows",
                project.id,
                len(collaborator_vals_list),
            )
            if collaborator_vals_list:
                collaborator_vals_list.sort(key=operator.itemgetter("partner_name"))
                result["collaborator_ids"] = [
                    Command.create(
                        {
                            "partner_id": collaborator["partner_id"],
                            "access_mode": collaborator["access_mode"],
                            "send_invitation": False,
                        }
                    )
                    for collaborator in collaborator_vals_list
                ]
        return {name: value for name, value in result.items() if name in fields_list}

    @api.model
    def _selection_target_model(self) -> list[tuple[str, str]]:
        project_model = self.env["ir.model"]._get("project.project")
        return [(project_model.model, project_model.name)]

    share_link = fields.Char(
        string="Public Link",
        help="Anyone with this link can access the project in read mode.",
    )
    collaborator_ids = fields.One2many(
        comodel_name="project.share.collaborator.wizard",
        inverse_name="parent_wizard_id",
        string="Collaborators",
    )
    existing_partner_ids = fields.Many2many(
        comodel_name="res.partner",
        export_string_translation=False,
        compute="_compute_existing_partner_ids",
    )

    @api.depends("res_model", "res_id")
    def _compute_resource_ref(self) -> None:
        for wizard in self:
            if wizard.res_model and wizard.res_model == "project.project":
                wizard.resource_ref = "%s,%s" % (
                    wizard.res_model,
                    wizard.res_id or 0,
                )
            else:
                wizard.resource_ref = None

    @api.depends("collaborator_ids")
    def _compute_existing_partner_ids(self) -> None:
        for wizard in self:
            wizard.existing_partner_ids = wizard.collaborator_ids.partner_id

    @dbg.timed
    def _sync_collaborators(self) -> None:
        for wizard in self:
            project = wizard.resource_ref
            existing = {c.partner_id: c for c in project.collaborator_ids}
            requested = {c.partner_id: c.access_mode for c in wizard.collaborator_ids}
            commands = [
                Command.delete(collaborator.id)
                for partner, collaborator in existing.items()
                if partner not in requested
            ]
            commands.extend(
                Command.update(existing[partner].id, {"access_mode": access_mode})
                for partner, access_mode in requested.items()
                if partner in existing and existing[partner].access_mode != access_mode
            )
            new_partners = project._get_new_collaborators(
                self.env["res.partner"].union(*requested)
            )
            commands.extend(
                Command.create(
                    {"partner_id": partner.id, "access_mode": requested[partner]}
                )
                for partner in new_partners
            )
            dbg.pipeline.debug(
                "[project:%s] share wizard sync: add=%s commands=%d",
                project.id,
                dbg.rec(new_partners),
                len(commands),
            )
            if commands:
                project.write({"collaborator_ids": commands})

    def action_share_record(self) -> dict[str, Any] | None:
        self.check_singleton()
        on_invite = self.env["res.users"]._get_signup_invitation_scope() == "b2b"
        new_portal_user = (
            self.collaborator_ids.filtered(
                lambda c: c.send_invitation and not c.partner_id.user_ids
            )
            and on_invite
        )
        dbg.logic.debug(
            "project.share.wizard.action_share_record %s: b2b=%s new_portal_user=%s",
            dbg.rec(self),
            on_invite,
            bool(new_portal_user),
        )
        if not new_portal_user:
            return self.action_send_mail()
        return {
            "name": _("Confirmation"),
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "views": [
                (
                    self.env.ref("project.project_share_wizard_confirm_form").id,
                    "form",
                )
            ],
            "res_model": "project.share.wizard",
            "res_id": self.id,
            "target": "new",
            "context": self.env.context,
        }

    @dbg.timed
    def action_send_mail(self) -> dict[str, Any]:
        dbg.pipeline.debug(
            "[share:%s] action_send_mail -> sync collaborators", dbg.rec(self)
        )
        self._sync_collaborators()
        result = {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "type": "success",
                "message": _("Project shared with your collaborators."),
                "next": {"type": "ir.actions.act_window_close"},
            },
        }
        new_collaborators = self.collaborator_ids.filtered("send_invitation").partner_id
        portal_partners = new_collaborators.filtered("user_ids")
        dbg.pipeline.debug(
            "[share:%s] public link -> %s, signup link -> %s",
            dbg.rec(self),
            dbg.rec(portal_partners),
            dbg.rec(new_collaborators - portal_partners),
        )
        invited = self._send_public_link(portal_partners) | self._send_signup_link(
            partners=new_collaborators.with_context({"signup_valid": True})
            - portal_partners
        )
        if invited:
            self._log_share_invitations(invited, record=self._get_shared_record())
        return result
