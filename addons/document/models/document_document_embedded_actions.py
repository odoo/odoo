from typing import Any

from odoo import _, api, models
from odoo.exceptions import AccessError, UserError
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class DocumentsDocument(models.Model):
    _inherit = "document.document"

    @api.depends_context("uid", "allowed_company_ids")
    @api.depends("folder_id", "type", "shortcut_document_id")
    def _compute_available_embedded_actions_ids(self) -> None:
        embedded_actions = self._get_folder_embedded_actions(self.folder_id.ids)
        embedded_actions_per_folder = {
            folder_id: actions.ids for folder_id, actions in embedded_actions.items()
        }
        self.available_embedded_actions_ids = False
        for document in self.filtered(
            lambda d: d.type != "folder" and not d.shortcut_document_id
        ):
            document.available_embedded_actions_ids = embedded_actions_per_folder.get(
                document.folder_id.id, False
            )

    @api.model
    def action_folder_embed_action(self, folder_id: int, action_id: int) -> list:
        if (
            not self.env.user.has_group("document.group_documents_user")
            and not self.env.su
        ):
            _debug.logic("embed_refused", reason="not_a_documents_user")
            raise AccessError(_("You are not allowed to pin/unpin embedded Actions."))
        embeddable_domain = self._get_domain_embeddable_server_action()
        action = (
            self.env["ir.actions.server"]
            .sudo()
            .search(Domain("id", "=", action_id) & embeddable_domain)
        )
        if not action:
            _debug.logic("embed_refused", reason="unknown_action")
            raise UserError(_("This action does not exist."))
        if action.type != "ir.actions.server":
            _debug.logic("embed_refused", reason="bad_action_type")
            raise UserError(_("You cannot pin that type of action."))
        folder = self.env["document.document"].browse(folder_id).sudo().exists()
        if not folder or folder.type != "folder":
            _debug.logic("embed_refused", reason="not_a_folder")
            raise UserError(_("You cannot pin an action on that document."))
        if folder.shortcut_document_id:
            return self.action_folder_embed_action(
                folder.shortcut_document_id.id, action_id
            )
        if (
            not self.env.su
            and folder.with_user(self.env.user).user_permission != "edit"
        ):
            _debug.logic("embed_refused", reason="folder_not_editable", folder=folder)
            raise AccessError(
                _("You are not allowed to pin/unpin actions on this folder.")
            )

        all_embedded_actions_sudo = (
            self.env["ir.embedded.actions"]
            .sudo()
            .search(
                Domain.AND(
                    [
                        self.env["ir.embedded.actions"]
                        .sudo()
                        ._get_domain_documents_embed_base(),
                        [
                            ("action_id", "=", action_id),
                            ("parent_res_id", "=", folder_id),
                        ],
                    ]
                )
            )
        )
        if all_embedded_actions_sudo:
            _debug.lifecycle("action_unpinned", folder=folder_id, action=action_id)
            all_embedded_actions_sudo.unlink()
        else:
            _debug.lifecycle("action_pinned", folder=folder_id, action=action_id)
            last_action = self.env["ir.embedded.actions"].search(
                [], order="sequence DESC", limit=1
            )
            embedded_action = self.env["ir.embedded.actions"].create(
                {
                    "name": action.name,
                    "parent_action_id": self.env.ref("document.document_action").id,
                    "action_id": action.id,
                    "parent_res_model": "document.document",
                    "parent_res_id": folder_id,
                    "group_ids": self.env.ref("base.group_user").ids,
                    "sequence": last_action.sequence + 1 if last_action else 1,
                }
            )
            action_name_translations = action._fields["name"]._get_stored_translations(
                action
            )
            for lang, translation in action_name_translations.items():
                if self.env["res.lang"]._get_lang_cached(lang):
                    embedded_action.with_context(lang=lang).name = translation

        return self.get_documents_actions(folder_id)

    @api.model
    def action_execute_embedded_action(self, action_id: int) -> Any:
        if self.env.user.share:
            _debug.logic("embed_run_refused", reason="share_user")
            raise AccessError(_("You are not allowed to execute embedded actions."))
        if self.env.context.get("active_model") != "document.document":
            _debug.logic("embed_run_refused", reason="wrong_active_model")
            raise UserError(_("Unavailable action."))
        ids = self.env.context.get(
            "active_ids",
            [self.env.context["active_id"]]
            if self.env.context.get("active_id")
            else [],
        )
        if not ids:
            _debug.logic("embed_run_refused", reason="no_active_ids")
            raise UserError(_("Missing documents reference."))

        embedded_action = self.env["ir.embedded.actions"].browse([action_id])
        if all(
            action_id in document.available_embedded_actions_ids.ids
            for document in self.browse(ids)
        ):
            with _debug.perf(
                "embed_run", cr=self.env.cr, action=action_id, documents=len(ids)
            ):
                return (
                    self.env["ir.actions.server"]
                    .with_context(documents_active_ids=ids)
                    .browse(embedded_action.action_id.id)
                    .run()
                )

        _debug.logic("embed_run_refused", reason="not_available_on_documents")
        raise UserError(_("Unavailable action."))

    @api.model
    def _data_embed_if_records_exist(
        self, folder_xmlid: str, server_action_xmlid: str
    ) -> None:
        if (action := self.env.ref(server_action_xmlid, raise_if_not_found=False)) and (
            folder := self.env.ref(folder_xmlid, raise_if_not_found=False)
        ):
            self.action_folder_embed_action(folder.id, action.id)

    def _embed_action(self, action_id: int) -> DocumentsDocument:
        IrEmbeddedActions = self.env["ir.embedded.actions"]
        embedded_actions = self._get_folder_embedded_actions(self.ids)

        new_embedding_folders = self.env["document.document"]
        for folder in self:
            if (
                action_id
                not in embedded_actions.get(folder.id, IrEmbeddedActions).action_id.ids
            ):
                folder.action_folder_embed_action(folder.id, action_id)
                new_embedding_folders |= folder
        return new_embedding_folders

    @api.model
    def _server_action_group_domain(self) -> Domain:
        return Domain(
            "group_ids", "any", [("id", "in", self.env.user.all_group_ids.ids)]
        ) | Domain("group_ids", "=", False)

    @api.model
    def _get_domain_base_server_actions(self) -> Domain:
        return Domain.AND(
            [
                [("model_id", "=", self.env["ir.model"]._get_id("document.document"))],
                [("usage", "in", ("ir_actions_server", "documents_embedded"))],
            ]
        )

    @api.model
    def check_automation_available(self) -> bool:
        return bool(
            self.env["ir.module.module"]
            .sudo()
            .search_count(
                [("name", "=", "automation"), ("state", "=", "installed")],
                limit=1,
            )
        )

    @api.model
    def get_documents_actions(self, folder_id: int) -> list:
        if not isinstance(folder_id, int):
            raise ValueError("Invalid folder_id")
        folder = self.env["document.document"].search([("id", "=", folder_id)])
        if not folder:
            raise UserError(_("This folder does not exist or is not accessible."))

        embedded_actions = self._get_folder_embedded_actions(folder.ids)
        embedded_actions = (
            embedded_actions[folder.id].action_id.ids if embedded_actions else []
        )

        actions = (
            self.env["ir.actions.server"]
            .sudo()
            .search(self._get_domain_embeddable_server_action())
        )
        return [
            {
                "id": action.id,
                "name": action.display_name,
                "is_embedded": action.id in embedded_actions,
            }
            for action in actions
        ]

    @api.model
    def _get_domain_embeddable_server_action(
        self, *, restrict_to_user_groups: bool = True
    ) -> Domain:
        candidate_domain = self._get_domain_base_server_actions()
        if restrict_to_user_groups:
            candidate_domain &= self._server_action_group_domain()
        candidate_actions_sudo = (
            self.env["ir.actions.server"].sudo()._search(candidate_domain)
        )
        return Domain.AND(
            [
                [("id", "in", candidate_actions_sudo)],
                [("parent_id", "=", False)],
                [("child_ids", "not any", [("id", "not in", candidate_actions_sudo)])],
            ]
        )

    def _get_folder_embedded_actions(self, folder_ids: list[int]) -> dict:
        folders_sudo = (
            self.env["document.document"]
            .sudo()
            .search(
                [
                    ("id", "in", folder_ids),
                    "|",
                    ("user_permission", "!=", "none"),
                    ("children_ids", "any", [("user_permission", "!=", "none")]),
                ]
            )
        )
        if not folders_sudo:
            return {}
        all_embedded_actions_sudo = (
            self.env["ir.embedded.actions"]
            .sudo()
            .search(
                domain=Domain.AND(
                    [
                        self.env["ir.embedded.actions"]
                        .sudo()
                        ._get_domain_documents_embed_base(),
                        [
                            (
                                "parent_res_id",
                                "in",
                                (folders_sudo + folders_sudo.shortcut_document_id).ids,
                            )
                        ],
                    ]
                ),
                order="sequence",
            )
        )
        accessible_server_actions_ids = (
            self.env["ir.actions.server"]
            .sudo()
            .search(
                Domain.AND(
                    [
                        [("id", "in", all_embedded_actions_sudo.action_id.ids)],
                        self._get_domain_embeddable_server_action(),
                    ]
                )
            )
            .ids
        )
        embedded_actions = all_embedded_actions_sudo.filtered(
            lambda e: e.action_id.id in accessible_server_actions_ids
        ).sudo(False)
        actions_per_folder = embedded_actions.grouped("parent_res_id")
        targets_to_shortcuts_sudo = folders_sudo.grouped("shortcut_document_id")
        actions_per_shortcut_folder = {
            shortcut_sudo.id: actions
            for target_sudo, shortcuts_sudo in targets_to_shortcuts_sudo.items()
            for shortcut_sudo in shortcuts_sudo
            if (actions := actions_per_folder.get(target_sudo.id))
        }
        return actions_per_folder | actions_per_shortcut_folder
