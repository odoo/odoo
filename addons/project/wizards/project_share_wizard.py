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
            collaborator_vals_list = []
            collaborator_ids = []
            for collaborator in project.collaborator_ids:
                collaborator_ids.append(collaborator.partner_id.id)
                collaborator_vals_list.append(
                    {
                        "partner_id": collaborator.partner_id.id,
                        "partner_name": collaborator.partner_id.display_name,
                        "access_mode": (
                            "edit_limited" if collaborator.limited_access else "edit"
                        ),
                    }
                )
            collaborator_vals_list.extend(
                {
                    "partner_id": follower.id,
                    "partner_name": follower.display_name,
                    "access_mode": "read",
                }
                for follower in project.message_partner_ids
                if follower.partner_share and follower.id not in collaborator_ids
            )
            dbg.logic.debug(
                "project.share.wizard.default_get [project:%s]: %d collaborators, "
                "%d prefilled rows",
                project.id,
                len(collaborator_ids),
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
            collaborator_ids_to_add = []
            collaborator_ids_to_add_with_limited_access = []
            collaborator_ids_vals_list = []
            project = wizard.resource_ref
            project_collaborator_ids_to_remove = [
                c.id
                for c in project.collaborator_ids
                if c.partner_id not in wizard.collaborator_ids.partner_id
            ]
            project_followers = project.message_partner_ids
            project_followers_to_add = []
            project_followers_to_remove = [
                partner.id
                for partner in project_followers
                if partner not in wizard.collaborator_ids.partner_id
                and partner.partner_share
            ]
            project_collaborator_per_partner_id = {
                c.partner_id.id: c for c in project.collaborator_ids
            }
            for collaborator in wizard.collaborator_ids:
                partner_id = collaborator.partner_id.id
                project_collaborator = project_collaborator_per_partner_id.get(
                    partner_id, self.env["project.collaborator"]
                )
                if collaborator.access_mode in ("edit", "edit_limited"):
                    limited_access = collaborator.access_mode == "edit_limited"
                    if not project_collaborator:
                        if limited_access:
                            collaborator_ids_to_add_with_limited_access.append(
                                partner_id
                            )
                        else:
                            collaborator_ids_to_add.append(partner_id)
                    elif project_collaborator.limited_access != limited_access:
                        collaborator_ids_vals_list.append(
                            Command.update(
                                project_collaborator.id,
                                {"limited_access": limited_access},
                            )
                        )
                elif project_collaborator:
                    project_collaborator_ids_to_remove.append(project_collaborator.id)
                if partner_id not in project_followers.ids:
                    project_followers_to_add.append(partner_id)
            if collaborator_ids_to_add:
                partners = project._get_new_collaborators(
                    self.env["res.partner"].browse(collaborator_ids_to_add)
                )
                collaborator_ids_vals_list.extend(
                    Command.create({"partner_id": partner_id})
                    for partner_id in partners.ids
                )
                project.task_ids.message_subscribe(partner_ids=partners.ids)
            if collaborator_ids_to_add_with_limited_access:
                partners = project._get_new_collaborators(
                    self.env["res.partner"].browse(
                        collaborator_ids_to_add_with_limited_access
                    )
                )
                collaborator_ids_vals_list.extend(
                    Command.create({"partner_id": partner_id, "limited_access": True})
                    for partner_id in partners.ids
                )
            if project_collaborator_ids_to_remove:
                collaborator_ids_vals_list.extend(
                    Command.delete(collaborator_id)
                    for collaborator_id in project_collaborator_ids_to_remove
                )
            dbg.pipeline.debug(
                "[project:%s] share wizard sync: add=%s add_limited=%s remove=%s "
                "commands=%d followers +%d/-%d",
                project.id,
                collaborator_ids_to_add,
                collaborator_ids_to_add_with_limited_access,
                project_collaborator_ids_to_remove,
                len(collaborator_ids_vals_list),
                len(project_followers_to_add),
                len(project_followers_to_remove),
            )
            project_vals = {}
            if collaborator_ids_vals_list:
                project_vals["collaborator_ids"] = collaborator_ids_vals_list
            if project_vals:
                project.write(project_vals)
            if project_followers_to_add:
                project._add_followers(
                    self.env["res.partner"].browse(project_followers_to_add)
                )
            if project_followers_to_remove:
                project.message_unsubscribe(project_followers_to_remove)

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
        partner_ids_in_readonly_mode = []
        partner_ids_in_edit_mode = []
        for collaborator in self.collaborator_ids:
            if not collaborator.send_invitation:
                continue
            if collaborator.access_mode == "read":
                partner_ids_in_readonly_mode.append(collaborator.partner_id.id)
            else:
                partner_ids_in_edit_mode.append(collaborator.partner_id.id)
        dbg.logic.debug(
            "project.share.wizard.action_send_mail %s: invite read=%s edit=%s",
            dbg.rec(self),
            partner_ids_in_readonly_mode,
            partner_ids_in_edit_mode,
        )
        invited = self.env["res.partner"]
        if partner_ids_in_edit_mode:
            new_collaborators = self.env["res.partner"].browse(partner_ids_in_edit_mode)
            portal_partners = new_collaborators.filtered("user_ids")
            dbg.pipeline.debug(
                "[share:%s] public link -> %s, signup link -> %s",
                dbg.rec(self),
                dbg.rec(portal_partners),
                dbg.rec(new_collaborators - portal_partners),
            )
            invited |= self._send_public_link(portal_partners)
            invited |= self._send_signup_link(
                partners=new_collaborators.with_context({"signup_valid": True})
                - portal_partners
            )
        if partner_ids_in_readonly_mode:
            invited |= self._send_share_links(
                self.env["res.partner"].browse(partner_ids_in_readonly_mode)
            )
        if invited:
            self._log_share_invitations(invited, record=self._get_shared_record())
        return result
